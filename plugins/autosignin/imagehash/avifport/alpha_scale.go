package avif

import (
	"encoding/binary"

	"github.com/gen2brain/gav1d/av1"
)

// libavif expands limited alpha before scaling coded samples to the output
// tile dimensions. With equal heights, its box filter reduces to horizontal
// linear filtering (or center sampling for a single column or a 3:1 ratio).
func normalizeAlpha(pic *av1.Picture, width, height int) (*av1.Picture, error) {
	if pic.Width == width && pic.Height == height {
		return pic, nil
	}
	if height != pic.Height || pic.Width > 16384 || pic.Height > 16384 || width > 32768 {
		return nil, ErrUnsupported
	}
	depth := pic.BitDepth
	if depth != 8 && depth != 10 && depth != 12 {
		return nil, ErrUnsupported
	}
	stepBytes := 1
	if depth > 8 {
		stepBytes = 2
	}
	out := &av1.Picture{Width: width, Height: height, BitDepth: depth, Layout: pic.Layout, FullRange: true}
	out.Stride[0] = width * stepBytes
	out.Data[0] = make([]byte, out.Stride[0]*height)
	nearest := pic.Width == 1 || pic.Width == 3*width
	double := !nearest && (width+1)/2 == pic.Width
	step := pic.Width << 16 / width
	start := (step >> 1) - 32768
	if nearest {
		start = step >> 1
	} else if width > pic.Width {
		step = ((pic.Width << 16) - 65537) / (width - 1)
		start = 0
	}
	shift := depth - 8
	alphaMax, limitedSpan := (1<<depth)-1, 219<<shift
	for y := range height {
		source := pic.Data[0][y*pic.Stride[0]:]
		dest := out.Data[0][y*out.Stride[0]:]
		sample := func(x int) int {
			v := int(source[x*stepBytes])
			if stepBytes == 2 {
				v = int(binary.NativeEndian.Uint16(source[x*stepBytes:]))
			}
			if !pic.FullRange {
				v = (min(limitedSpan, max(0, v-(16<<shift)))*alphaMax + limitedSpan/2) / limitedSpan
			}
			return v
		}
		coord := start
		for x := range width {
			left := min(pic.Width-1, coord>>16)
			v := sample(left)
			switch {
			case double:
				mid := x / 2
				neighbor := min(pic.Width-1, max(0, mid+x%2*2-1))
				if x == width-1 {
					neighbor = mid
				}
				v = (3*sample(mid) + sample(neighbor) + 2) >> 2
			case !nearest:
				delta := sample(min(pic.Width-1, left+1)) - v
				fraction := coord & 65535
				if stepBytes == 1 {
					// The installed x86 libyuv uses seven horizontal fraction bits.
					v += ((fraction>>9)*delta + 64) >> 7
				} else {
					v += (fraction*delta + 32768) >> 16
				}
			}
			if stepBytes == 1 {
				dest[x] = byte(v)
			} else {
				binary.NativeEndian.PutUint16(dest[2*x:], uint16(v))
			}
			coord += step
		}
	}
	pic.Release()
	return out, nil
}
