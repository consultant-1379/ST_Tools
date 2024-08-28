Summary: HSS ST Tool cnDiaProxy
Name: hss_st_cndiaproxy
Version: 1.0
Release: 1
License: -
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test

%description
cnDiaProxy: Proxy diameter messages from BAT to HSS used in cloud scenario

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
%attr(755, root, root) "%{prefix}/bin/cnDiaProxy"
%attr(755, root, root) "%{prefix}/share/cnDiaProxy.cfg"
