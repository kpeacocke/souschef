// Package main is the entry point for the SousChef Terraform provider
package main

import (
	"context"
	"flag"
	"log"
	"os"

	"github.com/hashicorp/terraform-plugin-framework/providerserver"
	"github.com/kpeacocke/terraform-provider-souschef/internal/provider"
)

// version is set during the release process to the release version of the binary
var version string = "dev"

var serve = providerserver.Serve
var logFatal = log.Fatal

func main() {
	if err := run(os.Args[1:]); err != nil {
		logFatal(err.Error())
	}
}

func run(args []string) error {
	flagSet := flag.NewFlagSet("souschef", flag.ContinueOnError)
	var debug bool

	flagSet.BoolVar(&debug, "debug", false, "set to true to run the provider with support for debuggers like delve")
	if err := flagSet.Parse(args); err != nil {
		return err
	}

	opts := providerserver.ServeOpts{
		Address: "registry.terraform.io/kpeacocke/souschef",
		Debug:   debug,
	}

	return serve(context.Background(), provider.New(version), opts)
}
