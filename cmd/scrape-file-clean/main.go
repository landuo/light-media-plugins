// ScrapeFileClean runs the local MoviePilot cleanup plugin.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/scrapefileclean"
)

func main() {
	manifest := scrapefileclean.Manifest()
	if err := manifest.Validate(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		if err := json.NewEncoder(os.Stdout).Encode(manifest); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		return
	}
	plugin := scrapefileclean.New()
	if err := plugins.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, manifest, plugin.Handle); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
