Summary: HSS ST Tool loadplotter
Name: hss_st_loadplotter
Version: 3.1
Release: 1
License: Ericsson
Group: --
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test

%description
LoadPlotter: Meassure, save and plot HSS CPU

%prep

%setup

%build
cd src
make 

%install
cd src
make install 

%clean
%{__rm} -rf %{buildroot}

%files 
%attr(755, root, root) "%{prefix}/bin/LoadPlotter"
%attr(755, root, root) "%{prefix}/share/loadplotter"
