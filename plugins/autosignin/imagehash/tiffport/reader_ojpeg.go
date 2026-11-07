package tiff

import (
	"bytes"
	"encoding/binary"
	"image"
	"io"

	jpegport "github.com/landuo/light-media-plugins/plugins/autosignin/imagehash/jpegport"
)

const (
	tJPEGInterchangeFormat       = 513
	tJPEGInterchangeFormatLength = 514
	tJPEGQTables                 = 519
	tJPEGDCTables                = 520
	tJPEGACTables                = 521
)

// An old JPEG interchange stream can hold the complete JPEG or just a prefix.
func (d *decoder) oldJPEGInterchange() *io.SectionReader {
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
	return io.NewSectionReader(d.r, offset, length)
}

// oldJPEGSource rebuilds the continuous JPEG scan from contiguous sample strips.
// libtiff tif_ojpeg.c inserts a restart marker between entropy-coded strips.
func (d *decoder) oldJPEGSource(l blockLayout, components, horizontal, vertical int) (jpegSource, error) {
	if l.padding || l.across != 1 {
		return nil, nil
	}
	interchange := d.oldJPEGInterchange()
	if interchange == nil {
		if _, found := d.ifd[tJPEGQTables]; !found {
			return nil, nil
		}
	}
	if d.config.Width > 65535 || d.config.Height > 65535 {
		return nil, FormatError("old JPEG dimensions exceed JPEG frame size")
	}
	var restart []byte
	if l.down > 1 {
		mcuWidth, mcuHeight := 8*horizontal, 8*vertical
		if l.height%mcuHeight != 0 {
			return nil, FormatError("old JPEG RowsPerStrip is not MCU aligned")
		}
		interval := ((l.width + mcuWidth - 1) / mcuWidth) * (l.height / mcuHeight)
		if interval > 65535 {
			return nil, FormatError("old JPEG restart interval exceeds 65535 MCUs")
		}
		restart = binary.BigEndian.AppendUint16(nil, uint16(interval))
	}
	strips := make([][2]int64, l.down)
	for i := range strips {
		offset, err := l.offsets.value(i)
		if err != nil {
			return nil, err
		}
		length, err := l.counts.value(i)
		if err != nil {
			return nil, err
		}
		if (offset == 0 || length == 0) && (l.down > 1 || interchange == nil) {
			return nil, FormatError("empty old JPEG strip")
		}
		strips[i] = [2]int64{int64(offset), int64(length)}
	}
	if interchange == nil && l.down == 1 {
		strip := sectionJPEGSource(d.r, strips[0][0], strips[0][1])
		// A self-contained JPEG strip takes precedence over separate tables.
		if readJPEGStart(strip()) == nil {
			if components == 1 {
				return nil, nil // Use the existing grayscale strip decoder.
			}
			return strip, nil
		}
	}
	var prefix []byte
	var err error
	if interchange == nil {
		prefix, err = d.oldJPEGTableHeader(components, horizontal, vertical, restart)
	} else if l.down > 1 {
		prefix, err = oldJPEGStripHeader(interchange, restart)
	}
	if err != nil {
		return nil, err
	}
	var interchangeOffset, interchangeLength int64
	if interchange != nil {
		_, base, length := interchange.Outer()
		position, _ := interchange.Seek(0, io.SeekCurrent)
		interchangeOffset, interchangeLength = base+position, length-position
	}
	return func() io.Reader {
		readers := []io.Reader{bytes.NewReader(prefix)}
		if interchangeLength != 0 {
			readers = append(readers, io.NewSectionReader(d.r, interchangeOffset, interchangeLength))
		}
		for i, strip := range strips {
			if i != 0 {
				readers = append(readers, bytes.NewReader([]byte{0xff, 0xd0 + byte((i-1)%8)}))
			}
			readers = append(readers, io.NewSectionReader(d.r, strip[0], strip[1]))
		}
		return io.MultiReader(append(readers, bytes.NewReader([]byte{0xff, 0xd9}))...)
	}, nil
}

// oldJPEGStripHeader rebuilds the header ahead of a multi-strip scan. A DRI
// already present in the interchange stream overrides the computed interval.
func oldJPEGStripHeader(r io.Reader, restart []byte) ([]byte, error) {
	if err := readJPEGStart(r); err != nil {
		return nil, err
	}
	var tables jpegTableSet
	var frame []byte
	for {
		marker, data, err := readJPEGMarker(r)
		if err != nil {
			return nil, err
		}
		switch {
		case marker == 0xda:
			if frame == nil {
				return nil, FormatError("missing old JPEG frame")
			}
			prefix := append([]byte{0xff, 0xd8}, tables.bytes()...)
			prefix = append(prefix, frame...)
			return appendJPEGMarker(appendJPEGRestart(prefix, restart), marker, data), nil
		case marker == 0xdb || marker == 0xc4:
			if err := tables.add(marker, data); err != nil {
				return nil, err
			}
		case marker == 0xc0 || marker == 0xc1:
			if frame != nil {
				return nil, FormatError("multiple old JPEG frames")
			}
			frame = appendJPEGMarker(nil, marker, data)
		case marker == 0xdd:
			if len(data) != 2 {
				return nil, FormatError("invalid old JPEG restart interval")
			}
			restart = data
		case jpegIgnoredMarker(marker):
		default:
			return nil, UnsupportedError("old JPEG interchange marker")
		}
	}
}

func appendJPEGRestart(prefix, restart []byte) []byte {
	if len(restart) == 2 && binary.BigEndian.Uint16(restart) != 0 {
		return appendJPEGMarker(prefix, 0xdd, restart)
	}
	return prefix
}

func (d *decoder) decodeOldJPEGYCbCr(l ycbcrLayout) (image.Image, error) {
	if l.tiled || d.ycbcr.horizontal != 2 || d.ycbcr.vertical != 2 {
		return nil, UnsupportedError("old JPEG YCbCr storage layout")
	}
	source, err := d.oldJPEGSource(blockLayout{width: l.width, height: l.height, across: l.across, down: l.down, offsets: l.offsets, counts: l.counts}, 3, 2, 2)
	if err != nil {
		return nil, err
	}
	if source == nil {
		return nil, UnsupportedError("missing old JPEG interchange stream")
	}
	samples, err := jpegport.DecodeTIFFYCbCr420(source(), d.config.Width, d.config.Height)
	if err != nil {
		return nil, err
	}
	img := image.NewRGBA(samples.Rect)
	for y := 0; y < d.config.Height; y++ {
		for x := 0; x < d.config.Width; x++ {
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
