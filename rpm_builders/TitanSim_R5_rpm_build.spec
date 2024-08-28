Summary: TitanSim_R5 
Name: titansim
Version: 5.0
Release: 5
License: GPL
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test
AutoReqProv: no

%description
TitanSim library for HSS BAT compilation

%prep
mkdir -p $RPM_BUILD_ROOT/$ST_TOOL_PATH/TCC_Releases
cp -r $ST_TOOL_PATH/TCC_Releases/TitanSim_R5 $RPM_BUILD_ROOT/$ST_TOOL_PATH/TCC_Releases

%clean
%{__rm} -rf %{buildroot}

%files 
%defattr(755,root,root)
"%{prefix}/TCC_Releases/TitanSim_R5"
