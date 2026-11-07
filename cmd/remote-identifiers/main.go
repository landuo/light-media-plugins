package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/remoteidentifiers"
)

func main() {
	manifest := remoteidentifiers.Manifest()
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
	p := remoteidentifiers.NewPlugin()
	if e := sdk.ServeConcurrentWithParallelHostCalls(context.Background(), os.Stdin, os.Stdout, manifest, p.Handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
