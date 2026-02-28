package main

import (
	"context"
	"os"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/providerserver"
)

func TestRunUsesServeOpts(t *testing.T) {
	originalServe := serve
	defer func() {
		serve = originalServe
	}()

	var gotOpts providerserver.ServeOpts
	serve = func(_ context.Context, _ func() provider.Provider, opts providerserver.ServeOpts) error {
		gotOpts = opts
		return nil
	}

	if err := run([]string{}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if gotOpts.Address != "registry.terraform.io/kpeacocke/souschef" {
		t.Fatalf("unexpected address: %s", gotOpts.Address)
	}
	if gotOpts.Debug {
		t.Fatal("expected debug to be false by default")
	}

	if err := run([]string{"-debug"}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !gotOpts.Debug {
		t.Fatal("expected debug to be true")
	}
}

func TestRunWithInvalidFlag(t *testing.T) {
	// Test with an unknown flag
	if err := run([]string{"-invalid-flag"}); err == nil {
		t.Fatal("expected error for invalid flag")
	}
}

func TestRunWithServeError(t *testing.T) {
	originalServe := serve
	defer func() {
		serve = originalServe
	}()

	// Mock serve to return an error
	serve = func(_ context.Context, _ func() provider.Provider, opts providerserver.ServeOpts) error {
		return testError{msg: "test error"}
	}

	if err := run([]string{}); err == nil {
		t.Fatal("expected error from serve")
	}
}

func TestMainSuccessDoesNotCallLogFatal(t *testing.T) {
	originalServe := serve
	originalLogFatal := logFatal
	originalArgs := os.Args
	defer func() {
		serve = originalServe
		logFatal = originalLogFatal
		os.Args = originalArgs
	}()

	serve = func(_ context.Context, _ func() provider.Provider, _ providerserver.ServeOpts) error {
		return nil
	}
	os.Args = []string{"souschef"}

	called := false
	logFatal = func(_ ...interface{}) {
		called = true
	}

	main()
	if called {
		t.Fatal("did not expect logFatal to be called")
	}
}

func TestMainErrorCallsLogFatal(t *testing.T) {
	originalServe := serve
	originalLogFatal := logFatal
	originalArgs := os.Args
	defer func() {
		serve = originalServe
		logFatal = originalLogFatal
		os.Args = originalArgs
	}()

	serve = func(_ context.Context, _ func() provider.Provider, _ providerserver.ServeOpts) error {
		return testError{msg: "boom"}
	}
	os.Args = []string{"souschef"}

	called := false
	logFatal = func(_ ...interface{}) {
		called = true
	}

	main()
	if !called {
		t.Fatal("expected logFatal to be called")
	}
}

type testError struct {
	msg string
}

func (e testError) Error() string {
	return e.msg
}
