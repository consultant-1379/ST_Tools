Summary: HSS ST Tool ConKeeper
Name: hss_st_conkeeper
Version: 1.3
Release: 4
License: GPL
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test

%description
ConKeeper: Keep tcp connections up

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
%attr(755, root, root) "%{prefix}/bin/ConKeeper"
%attr(755, root, root) "%{prefix}/share/conKeeper"
