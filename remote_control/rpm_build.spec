Summary: HSS ST Tool RemoteControl
Name: hss_st_remotecontrol
Version: 1.1
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
CpsMonitor: Send UDP messages

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
%attr(755, root, root) "%{prefix}/bin/RemoteControl"
