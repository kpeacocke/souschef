#!/bin/bash
# Habitat plan for nginx web server

pkg_name=nginx
pkg_origin=core
pkg_version="1.25.3"
pkg_maintainer="SousChef Team <team@souschef.io>"
pkg_license=('BSD-2-Clause')
pkg_description="A high performance web server and reverse proxy"
pkg_upstream_url="https://nginx.org"
pkg_source="https://nginx.org/download/${pkg_name}-${pkg_version}.tar.gz"
pkg_shasum="f9187468ff2eb159260bfd53867c25ff8e334726237acf5021f65f95f8d3f945"
pkg_filename="${pkg_name}-${pkg_version}.tar.gz"
pkg_dirname="${pkg_name}-${pkg_version}"

# Build dependencies
pkg_build_deps=(
  core/gcc
  core/make
  core/openssl
  core/pcre
  core/zlib
)

# Runtime dependencies
pkg_deps=(
  core/glibc
  core/openssl
  core/pcre
  core/zlib
)

# Exposed ports
pkg_exports=(
  [port]=http.port
  [ssl-port]=http.ssl_port
)

# Service bindings
pkg_binds_optional=(
  [backend]="port"
)

# Service configuration
pkg_exposes=(port ssl-port)
pkg_svc_run="nginx -g 'daemon off;'"
pkg_svc_user="root"
pkg_svc_group="root"

do_build() {
  ./configure \
    --prefix="$pkg_prefix" \
    --conf-path="$pkg_svc_config_path/nginx.conf" \
    --error-log-path=stderr \
    --http-log-path=/dev/stdout \
    --pid-path="$pkg_svc_var_path/nginx.pid" \
    --lock-path="$pkg_svc_var_path/nginx.lock" \
    --user=hab \
    --group=hab \
    --with-threads \
    --with-http_ssl_module \
    --with-http_v2_module \
    --with-http_realip_module \
    --with-http_gzip_static_module \
    --with-http_stub_status_module
  make
}

do_install() {
  make install
}
