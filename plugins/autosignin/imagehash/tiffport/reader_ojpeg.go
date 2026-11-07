package tiff

import (
	"image"
	"io"

	jpegport "github.com/landuo/light-media-plugins/plugins/autosignin/imagehash/jpegport"
)

const (
	tJPEGInterchangeFormat       = 513
	tJPEGInterchangeFormatLength = 514
)

// oldJPEGInterchange reads a single strip with a JPEG interchange stream.
// Compression 6 can store the header before a separate entropy-coded strip,
// or point the strip into the complete interchange stream.
func (d *decoder) oldJPEGInterchange(b tiffBlock) jpegSource {
	if b.x != 0 || b.y != 0 || b.width != d.config.Width || b.height != d.config.Height || d.firstVal(tTileWidth) != 0 {
		return nil
	}
	offsetField := d.ifd[tJPEGInterchangeFormat]
	lengthField := d.ifd[tJPEGInterchangeFormatLength]
	if d.byteOrder.Uint16(offsetField[2:4]) != dtLong || d.byteOrder.Uint32(offsetField[4:8]) != 1 ||
		d.byteOrder.Uint16(lengthField[2:4]) != dtLong || d.byteOrder.Uint32(lengthField[4:8]) != 1 {
		return nil
	}
	offset := int64(d.byteOrder.Uint32(offsetField[8:12]))
	length := int64(d.byteOrder.Uint32(lengthField[8:12]))
	if offset == 0 || length == 0 {
		return nil
	}
	return func() io.Reader {
		return io.MultiReader(io.NewSectionReader(d.r, offset, length), io.NewSectionReader(d.r, b.offset, b.n))
	}
}

func (d *decoder) decodeOldJPEGYCbCr(l ycbcrLayout) (image.Image, error) {
	if l.tiled || l.down != 1 || d.ycbcr.horizontal != 2 || d.ycbcr.vertical != 2 {
		return nil, UnsupportedError("old JPEG YCbCr storage layout")
	}
	offset, err := l.offsets.value(0)
	if err != nil {
		return nil, err
	}
	n, err := l.counts.value(0)
	if err != nil {
		return nil, err
	}
	source := d.oldJPEGInterchange(tiffBlock{offset: int64(offset), n: int64(n), width: l.width, height: l.height})
	if source == nil {
		return nil, UnsupportedError("missing old JPEG interchange stream")
	}
	samples, err := jpegport.DecodeTIFFYCbCr420(source(), l.width, l.height)
	if err != nil {
		return nil, err
	}
	img := image.NewRGBA(samples.Rect)
	for y := 0; y < l.height; y++ {
		for x := 0; x < l.width; x++ {
			s := samples.YCbCrAt(x, y)
			luma, cb, cr := int(s.Y), int(s.Cb)-128, int(s.Cr)-128
			// libtiff tif_color.c uses separately rounded red and blue
			// deltas and a single rounding for the combined green delta.
			r := luma + ((91881*cr + 32768) >> 16)
			g := luma + ((-22553*cb - 46802*cr + 32768) >> 16)
			b := luma + ((116130*cb + 32768) >> 16)
			i := img.PixOffset(x, y)
			img.Pix[i] = byte(min(max(r, 0), 255))
			img.Pix[i+1] = byte(min(max(g, 0), 255))
			img.Pix[i+2] = byte(min(max(b, 0), 255))
			img.Pix[i+3] = 255
		}
	}
	return img, nil
}
