Summary: TitanSim_R7 
Name: titansim
Version: 7.0
Release: 3
License: GPL
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.se
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test
AutoReqProv: no

%description
TitanSim library for HSS BAT compilation

%prep
mkdir -p $RPM_BUILD_ROOT/$ST_TOOL_PATH/TCC_Releases
cp -r $SOURCE_PATH/* $RPM_BUILD_ROOT/$ST_TOOL_PATH/TCC_Releases

%clean
%{__rm} -rf %{buildroot}

%files 
%defattr(755,root,root)
"%{prefix}/TCC_Releases"
