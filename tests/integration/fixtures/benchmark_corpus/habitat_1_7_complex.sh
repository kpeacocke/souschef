# Habitat plan syntax represented by the 1.7 fixture family.
pkg_name="example-web"
pkg_origin="benchmark"
pkg_version="2.4.1"
pkg_maintainer="SousChef test fixtures"
pkg_license=('MIT')
pkg_description="Deterministic multi-component benchmark package"
pkg_upstream_url="https://example.invalid/example-web"
pkg_build_deps=(core/gcc core/make)
pkg_deps=(core/glibc core/nginx core/openssl)
pkg_exports=(
  [http]=web.port
  [https]=web.https_port
)
pkg_exposes=(http https)
pkg_svc_user="root"
pkg_svc_group="root"
pkg_svc_run="nginx -g 'daemon off;'"

do_build() {
  ./configure --prefix="${pkg_prefix}"
  make -j"$(nproc)"
  make install
}

do_install() {
  install -d "${pkg_prefix}/var/log/example-web"
  cp -r config "${pkg_prefix}/config"
}
