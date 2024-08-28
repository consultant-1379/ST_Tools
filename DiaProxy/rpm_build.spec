Summary: HSS ST Tool DiaProxy
Name: hss_st_diaproxy
Version: 5.0
Release: 35
License: -
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test

%description
DiaProxy: Proxy diameter messages from BAT to HSS

%prep

%setup

%build
cd source
make 

%install
cd source
make install 

%clean
%{__rm} -rf %{buildroot}

%files 
%attr(755, root, root) "%{prefix}/bin/DiaProxy5.0"
%attr(755, root, root) "%{prefix}/share/DiaProxy"
