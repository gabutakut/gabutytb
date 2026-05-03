project('gabutytb', version: '1.0', meson_version: '>= 0.62.0',)

python = import('python')
py = python.find_installation('python3', required: true)
gnome  = import('gnome')

pkgdatadir = get_option('prefix') / get_option('datadir') / 'gabutytb'

install_data(
  'splash.py',
  'main.py',
  'window.py',
  'server.py',
  install_dir: pkgdatadir,
)

configure_file(
  input:  'com.github.gabutakut.gabutytb.in',
  output: 'com.github.gabutakut.gabutytb',
  configuration: {
    'PYTHON'     : py.full_path(),
    'PKGDATADIR' : pkgdatadir,
    'VERSION'    : meson.project_version(),
  },
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

install_data(
  'data/com.github.gabutakut.gabutytb.desktop',
  install_dir: get_option('datadir') / 'applications',
)

install_data(
  'data/com.github.gabutakut.gabutytb.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo',
)

install_data(
  'data/icons/com.github.gabutakut.gabutytb.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)