package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	merge "github.com/landuo/light-media-plugins/plugins/mergemessagenotify"
	mergesmtp "github.com/landuo/light-media-plugins/plugins/mergemessagenotify/smtp"
)

func main() {
	manifest := merge.Manifest()
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
	worker := merge.NewWorker(sendSMTP)
	if err := sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, manifest, worker.Handle); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func sendSMTP(ctx context.Context, config map[string]any, request merge.SMTPRequest) error {
	binding, err := mergesmtp.BindingFromTrustedConfig(config)
	if err != nil {
		return err
	}
	adapter, err := mergesmtp.New(binding, mergesmtp.Options{})
	if err != nil {
		return err
	}
	return adapter.Send(ctx, request)
}
