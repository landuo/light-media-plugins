package iyuuautoseed

import (
	"context"
	sdk "github.com/landuo/light-media-plugins/internal/sdk"
)

func newHostAPITransport(ctx context.Context, caller sdk.HostCaller, token string, guard func(context.Context) error) (*APITransport, error) {
	// Workers intentionally do not inherit host proxy environment variables.
	// IyuuHelper passes proxies=None: use only the trusted host environment,
	// not the application's explicit site proxy settings.
	proxy, err := (sdk.Network{Host: caller}).ProxySettings(ctx)
	if err != nil {
		return nil, err
	}
	return NewAPITransport(TrustedAPIBinding{Token: token}, APITransportOptions{Guard: guard, Environment: proxy.Environment})
}
