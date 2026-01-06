#!/bin/bash
# Habitat plan for PostgreSQL database

pkg_name=postgresql
pkg_origin=core
pkg_version="14.5"
pkg_maintainer="SousChef Team <team@souschef.io>"
pkg_license=('PostgreSQL')
pkg_description="PostgreSQL is a powerful, open source object-relational database system"
pkg_upstream_url="https://www.postgresql.org"
pkg_source="https://ftp.postgresql.org/pub/source/v${pkg_version}/${pkg_name}-${pkg_version}.tar.gz"
pkg_shasum="d5bc6c2b80f0c0da8e6bbbca0b0ac0e8c2f2e0c2b8f1e3d4c7a9b5e4f3d2c1a0"

# Build dependencies
pkg_build_deps=(
  core/gcc
  core/make
  core/readline
  core/zlib
)

# Runtime dependencies
pkg_deps=(
  core/glibc
  core/readline
  core/zlib
  core/openssl
)

# Exposed ports
pkg_exports=(
  [port]=postgresql.port
)

# Service configuration
pkg_exposes=(port)
pkg_svc_run="postgres -D $pkg_svc_data_path/pgdata -c config_file=$pkg_svc_config_path/postgresql.conf"
pkg_svc_user="hab"
pkg_svc_group="hab"

do_build() {
  ./configure \
    --prefix="$pkg_prefix" \
    --with-openssl \
    --with-readline
  make world
}

do_install() {
  make install-world
}

do_init() {
  mkdir -p "$pkg_svc_data_path/pgdata"
  initdb -D "$pkg_svc_data_path/pgdata" -U hab
}
