Summary: HSS ST Tool scenarioDeployGenerator
Name: hss_st_scenariodeploygenerator
Version: 1.13
Release: 1
License: GPL
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test

%description
scenarioDeployGenerator: Create cfg for HSS BAT execution

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
%attr(755, root, root) "%{prefix}/bin/scenarioDeployGenerator"
