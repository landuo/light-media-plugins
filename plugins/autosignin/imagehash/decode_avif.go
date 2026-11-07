package imagehash

import (
	"bytes"
	"encoding/binary"
	"image"

	"github.com/gen2brain/gav1d/av1"
	avif "github.com/landuo/light-media-plugins/plugins/autosignin/imagehash/avifport"
)

func decodeAVIF(data []byte) (Raster, error) {
	cfg, err := avif.DecodeConfig(bytes.NewReader(data))
	if err != nil {
		return Raster{}, err
	}
	if err = checkImageSize(cfg.Width, cfg.Height); err != nil {
		return Raster{}, err
	}
	// Pillow checks the container transform before loading. Do not silently add
	// an independent decoder allocation quota below that existing source limit.
	img, ci, err := avif.DecodeColor(bytes.NewReader(data), avif.Options{
		ToYCbCr: true, FrameSizeLimit: cfg.Width * cfg.Height, ConvertPicture: highDepthAVIF,
	})
	if err != nil {
		return Raster{}, err
	}
	if converted, ok := img.(*image.RGBA); ok {
		return fromImage(converted, "RGB")
	}
	var yuv *image.YCbCr
	var alpha *image.NYCbCrA
	switch p := img.(type) {
	case *image.YCbCr:
		yuv = p
	case *image.NYCbCrA:
		yuv, alpha = &p.YCbCr, p
	}
	if yuv == nil {
		// Fixed Pillow _avif.c exposes irot/imir as EXIF metadata rather than
		// transforming samples. An opaque extra storage alpha byte is harmless
		// to the resize; keep actual alpha from the decoder without guessing at
		// auxl item relationships by searching arbitrary container bytes.
		return fromImage(img, "RGBA")
	}
	coeff, ok := avifYUVConstants(ci.Matrix, ci.FullRange)
	if !ok {
		// The decoder implements the less common CICP matrices too. Keep their
		// signalled color space rather than treating every stream as BT.601.
		img, err = avif.Decode(bytes.NewReader(data), avif.Options{FrameSizeLimit: cfg.Width * cfg.Height})
		if err != nil {
			return Raster{}, err
		}
		mode := "RGB"
		if alpha != nil {
			mode = "RGBA"
		}
		return fromImage(img, mode)
	}
	b := yuv.Bounds()
	mode, channels := "RGB", 3
	if alpha != nil {
		mode, channels = "RGBA", 4
	}
	r := Raster{Mode: mode, Width: b.Dx(), Height: b.Dy(), Pixels: make([]byte, b.Dx()*b.Dy()*channels)}
	for y := b.Min.Y; y < b.Max.Y; y++ {
		for x := b.Min.X; x < b.Max.X; x++ {
			u := avifChroma(yuv, yuv.Cb, x, y) - 128
			v := avifChroma(yuv, yuv.Cr, x, y) - 128
			at := ((y-b.Min.Y)*b.Dx() + x - b.Min.X) * channels
			r.Pixels[at], r.Pixels[at+1], r.Pixels[at+2] = avifRGB8(int(yuv.Y[yuv.YOffset(x, y)]), u, v, coeff)
			if alpha != nil {
				r.Pixels[at+3] = alpha.A[alpha.AOffset(x, y)]
			}
		}
	}
	return r, nil
}

// Pillow requests RGB8 or RGBA8 from libavif. Opaque color uses byte-plane
// chroma interpolation, and opaque monochrome uses full-depth luma.
func highDepthAVIF(pic, alpha *av1.Picture, ci avif.ColorInfo, premultiplied bool) image.Image {
	if pic.BitDepth != 10 && pic.BitDepth != 12 {
		return nil
	}
	coeff, ok := avifYUVConstants(ci.Matrix, ci.FullRange)
	if !ok {
		return nil
	}
	rect := image.Rect(0, 0, pic.Width, pic.Height)
	shift := pic.BitDepth - 8
	sx, sy := 1, 1
	switch pic.Layout {
	case av1.LayoutI420:
		sx, sy = 2, 2
	case av1.LayoutI422:
		sx = 2
	case av1.LayoutI400, av1.LayoutI444:
	default:
		return nil
	}
	if alpha != nil {
		if alpha.Layout != av1.LayoutI400 || alpha.BitDepth != pic.BitDepth {
			return nil
		}
		return highDepthAVIFAlpha(pic, alpha, rect, sx, sy, coeff, premultiplied)
	}
	if pic.Layout == av1.LayoutI400 {
		bias, scale := 0, (1<<pic.BitDepth)-1
		if !ci.FullRange {
			bias, scale = 16<<shift, 219<<shift
		}
		out := image.NewRGBA(rect)
		for y := 0; y < pic.Height; y++ {
			for x := 0; x < pic.Width; x++ {
				luma := float32(avifSample16(pic, 0, x, y)-bias) / float32(scale)
				value := byte(float32(min(1, max(0, luma))*255) + 0.5)
				at := out.PixOffset(x, y)
				out.Pix[at], out.Pix[at+1], out.Pix[at+2], out.Pix[at+3] = value, value, value, 255
			}
		}
		return out
	}
	out := image.NewRGBA(rect)
	cb := func(x, y int) int { return avifSample16(pic, 1, x, y) >> shift }
	cr := func(x, y int) int { return avifSample16(pic, 2, x, y) >> shift }
	for y := 0; y < pic.Height; y++ {
		for x := 0; x < pic.Width; x++ {
			u := interpolateAVIFChroma(rect, sx, sy, x, y, cb) - 128
			v := interpolateAVIFChroma(rect, sx, sy, x, y, cr) - 128
			luma := avifSample16(pic, 0, x, y) >> shift
			at := out.PixOffset(x, y)
			out.Pix[at], out.Pix[at+1], out.Pix[at+2] = avifRGB8(luma, u, v, coeff)
			out.Pix[at+3] = 255
		}
	}
	return out
}

// Pillow asks libavif for straight RGBA8. libyuv uses native high-depth
// conversion for 10-bit color and 12-bit 4:2:0, and byte planes otherwise.
func highDepthAVIFAlpha(pic, alpha *av1.Picture, rect image.Rectangle, sx, sy int, coeff [6]int, premultiplied bool) image.Image {
	shift := pic.BitDepth - 8
	maxSample := (1 << pic.BitDepth) - 1
	mono := pic.Layout == av1.LayoutI400
	nearest := pic.BitDepth == 12 && pic.Layout == av1.LayoutI420
	highDepth := !mono && (pic.BitDepth == 10 || nearest)
	roundedAlpha := mono || nearest
	chroma := func(plane, x, y int) int {
		if nearest {
			return avifSample16(pic, plane, x/sx, y/sy) >> shift
		}
		sample := func(cx, cy int) int {
			value := avifSample16(pic, plane, cx, cy)
			if !highDepth {
				value >>= shift
			}
			return value
		}
		value := interpolateAVIFChroma(rect, sx, sy, x, y, sample)
		if highDepth {
			value >>= shift
		}
		return value
	}
	out := image.NewNRGBA(rect)
	for y := 0; y < pic.Height; y++ {
		for x := 0; x < pic.Width; x++ {
			luma := avifSample16(pic, 0, x, y)
			word := (luma >> shift) * 257
			if highDepth {
				word = (luma << (16 - pic.BitDepth)) | (luma >> (2*pic.BitDepth - 16))
			}
			u, v := 0, 0
			if !mono {
				u, v = chroma(1, x, y)-128, chroma(2, x, y)-128
			}
			r, g, b := avifRGBFromWord(word, u, v, coeff)
			a := avifSample16(alpha, 0, x, y)
			if !alpha.FullRange {
				span := 219 << shift
				a = (min(span, max(0, a-(16<<shift)))*maxSample + span/2) / span
			}
			a8 := a >> shift
			if roundedAlpha {
				a8 = int(float32(float32(a)/float32(maxSample)*255) + 0.5)
			}
			if premultiplied && a8 != 255 {
				inverse := 0
				if a8 > 0 {
					inverse = min(65535, 65536/a8)
				}
				unattenuate := func(c byte) byte { return byte(min(255, int(c)*257*inverse>>16)) }
				r, g, b = unattenuate(r), unattenuate(g), unattenuate(b)
			}
			at := out.PixOffset(x, y)
			out.Pix[at], out.Pix[at+1], out.Pix[at+2], out.Pix[at+3] = r, g, b, byte(a8)
		}
	}
	return out
}

func avifSample16(pic *av1.Picture, plane, x, y int) int {
	return int(binary.NativeEndian.Uint16(pic.Data[plane][y*pic.Stride[plane]+2*x:]))
}

func avifRGB8(luma, u, v int, coeff [6]int) (byte, byte, byte) {
	return avifRGBFromWord(luma*257, u, v, coeff)
}

func avifRGBFromWord(word, u, v int, coeff [6]int) (byte, byte, byte) {
	y := (word * coeff[0] >> 16) + coeff[1]
	clamp := func(value int) byte { return byte(min(255, max(0, value>>6))) }
	return clamp(y + v*coeff[5]), clamp(y - u*coeff[3] - v*coeff[4]), clamp(y + u*coeff[2])
}

// libyuv YuvPixel/MAKEYUVCONSTANTS: fixed-point color conversion follows the
// source Pillow/libavif output. The decoder's float conversion differs by one
// sample and can change the mean threshold even when its AV1 planes are exact.
// Coefficients: YG,YB,UB,UG,VG,VR. Notices are in LIBYUV-*.
func avifYUVConstants(matrix uint16, full bool) ([6]int, bool) {
	if full {
		switch matrix {
		case 1:
			return [6]int{16320, 32, 119, 12, 30, 101}, true
		case 2, 5, 6:
			return [6]int{16320, 32, 113, 22, 46, 90}, true
		case 9:
			return [6]int{16320, 32, 120, 11, 37, 94}, true
		}
	} else {
		switch matrix {
		case 1:
			return [6]int{18997, -1160, 128, 14, 34, 115}, true
		case 2, 5, 6:
			return [6]int{18997, -1160, 128, 25, 52, 102}, true
		case 9:
			return [6]int{19003, -1160, 128, 12, 42, 107}, true
		}
	}
	return [6]int{}, false
}

// ScaleRowUp2_Bilinear/Linear: perform the byte-plane rounding before the
// matrix, rather than applying a float interpolation to already normalized UV.
func avifChroma(p *image.YCbCr, plane []byte, x, y int) int {
	sx, sy := 1, 1
	switch p.SubsampleRatio {
	case image.YCbCrSubsampleRatio420:
		sx, sy = 2, 2
	case image.YCbCrSubsampleRatio422:
		sx = 2
	case image.YCbCrSubsampleRatio440:
		sy = 2
	}
	return interpolateAVIFChroma(p.Rect, sx, sy, x, y, func(cx, cy int) int {
		return int(plane[(cy-p.Rect.Min.Y/sy)*p.CStride+cx-p.Rect.Min.X/sx])
	})
}

func interpolateAVIFChroma(rect image.Rectangle, sx, sy, x, y int, at func(int, int) int) int {
	x0, y0 := x/sx, y/sy
	x1, y1 := x0, y0
	// The filtered libyuv rows copy the final source column at the right
	// edge, including when the destination width is odd.
	if sx == 2 && x < rect.Max.X-1 {
		x1 += x%2*2 - 1
	}
	if sy == 2 {
		y1 += y%2*2 - 1
	}
	x1 = min((rect.Max.X-1)/sx, max(rect.Min.X/sx, x1))
	y1 = min((rect.Max.Y-1)/sy, max(rect.Min.Y/sy, y1))
	if sx == 2 && sy == 2 {
		return (9*at(x0, y0) + 3*at(x1, y0) + 3*at(x0, y1) + at(x1, y1) + 8) >> 4
	}
	if sx == 2 || sy == 2 {
		return (3*at(x0, y0) + at(x1, y1) + 2) >> 2
	}
	return at(x0, y0)
}
