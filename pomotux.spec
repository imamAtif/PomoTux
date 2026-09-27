# Keep Version in sync with pomotux.__version__ and debian/changelog.
Name:           pomotux
Version:        0.2.0
Release:        1%{?dist}
Summary:        Lightweight premium Pomodoro timer for Linux
License:        GPL-3.0-only
URL:            https://github.com/imamAtif/PomoTux
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
Requires:       python3-PySide6
Requires:       hicolor-icon-theme

%description
PomoTux is a fast, native Pomodoro timer for Linux with tasks,
stats, tray integration and custom themes.

%prep
%autosetup -n %{name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
install -Dpm644 packaging/io.github.pomotux.desktop %{buildroot}%{_datadir}/applications/io.github.pomotux.desktop
for s in 16 32 48 64 128 256 512; do
  install -Dpm644 packaging/icons/hicolor/${s}x${s}/apps/io.github.pomotux.png %{buildroot}%{_datadir}/icons/hicolor/${s}x${s}/apps/io.github.pomotux.png
done
install -Dpm644 packaging/icons/io.github.pomotux.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.pomotux.svg

%files
%{_bindir}/pomotux
%{python3_sitelib}/main.py
%{python3_sitelib}/__pycache__/main.*.pyc
%{python3_sitelib}/pomotux/
%{python3_sitelib}/pomotux-*.dist-info/
%{_datadir}/applications/io.github.pomotux.desktop
%{_datadir}/icons/hicolor/*/apps/io.github.pomotux.png
%{_datadir}/icons/hicolor/scalable/apps/io.github.pomotux.svg

%changelog
* Sun Sep 27 2026 PomoTux Developers - 0.2.0-1
- Stable release: pause indication, working sounds, new icon
* Sun Sep 27 2026 PomoTux Developers - 0.1.0-1
- Initial package
