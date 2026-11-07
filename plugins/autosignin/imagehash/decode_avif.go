package imagehash

import (
	"bytes"
	"image"

	"github.com/gen2brain/gav1d/avif"
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
		ToYCbCr: true, FrameSizeLimit: cfg.Width * cfg.Height,
	})
	if err != nil {
		return Raster{}, err
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
			yy := (int(yuv.Y[yuv.YOffset(x, y)]) * 257 * coeff[0] >> 16) + coeff[1]
			at := ((y-b.Min.Y)*b.Dx() + x - b.Min.X) * channels
			r.Pixels[at] = byte(min(255, max(0, (yy+v*coeff[5])>>6)))
			r.Pixels[at+1] = byte(min(255, max(0, (yy-u*coeff[3]-v*coeff[4])>>6)))
			r.Pixels[at+2] = byte(min(255, max(0, (yy+u*coeff[2])>>6)))
			if alpha != nil {
				r.Pixels[at+3] = alpha.A[alpha.AOffset(x, y)]
			}
		}
	}
	return r, nil
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
	x0, y0 := x/sx, y/sy
	x1, y1 := x0, y0
	if sx == 2 {
		x1 += x%2*2 - 1
	}
	if sy == 2 {
		y1 += y%2*2 - 1
	}
	x1 = min((p.Rect.Max.X-1)/sx, max(p.Rect.Min.X/sx, x1))
	y1 = min((p.Rect.Max.Y-1)/sy, max(p.Rect.Min.Y/sy, y1))
	at := func(cx, cy int) int { return int(plane[(cy-p.Rect.Min.Y/sy)*p.CStride+cx-p.Rect.Min.X/sx]) }
	if sx == 2 && sy == 2 {
		return (9*at(x0, y0) + 3*at(x1, y0) + 3*at(x0, y1) + at(x1, y1) + 8) >> 4
	}
	if sx == 2 || sy == 2 {
		return (3*at(x0, y0) + at(x1, y1) + 2) >> 2
	}
	return at(x0, y0)
}
