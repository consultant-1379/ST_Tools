Summary: HSS ST Tool loadlogger
Name: hss_st_loadlogger
Version: 3.0
Release: 6
License: GPL
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test

%description
CpsMonitor: Log CPU and memory usage

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
%attr(755, root, root) "%{prefix}/bin/loadlogger.3.0"
%attr(755, root, root) "%{prefix}/share/loadlogger"
