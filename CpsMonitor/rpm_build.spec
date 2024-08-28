Summary: HSS ST Tool CpsMonitor
Name: hss_st_cpsmonitor
Version: 1.0
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
CpsMonitor: Handle CPS during HSS traffic execution

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
%attr(755, root, root) "%{prefix}/bin/CpsMonitor"
%attr(755, root, root) "%{prefix}/share/CpsMonitor"
