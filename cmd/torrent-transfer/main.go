// TorrentTransfer is one persistent standard SDK worker for all host instances.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/torrenttransfer"
	"os"
)

func main() {
	manifest := torrenttransfer.Manifest()
	if e := manifest.Validate(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(2)
	}
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		if e := json.NewEncoder(os.Stdout).Encode(manifest); e != nil {
			fmt.Fprintln(os.Stderr, e)
			os.Exit(2)
		}
		return
	}
	p := torrenttransfer.New()
	if e := plugins.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, manifest, p.Handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
