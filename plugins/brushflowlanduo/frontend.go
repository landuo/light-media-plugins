package brushflowlanduo

import sdk "github.com/landuo/light-media-plugins/internal/sdk"

func Frontend() *sdk.Frontend {
	return &sdk.Frontend{
		Contract:    sdk.FrontendFederationContract,
		Root:        "dist/assets",
		Entry:       "remoteEntry.js",
		Exposes:     []string{"Config", "Page", "Dashboard", "AppPage"},
		Shared:      []string{"vue", "vuetify", "vuetify/styles"},
		APIContract: sdk.FrontendAPIContract,
	}
}
