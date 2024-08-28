Summary: TitanSim_OSS 
Name: titansim_oss
Version: 8.6
Release: 1
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
TitanSim OSS library for HSS BAT compilation

%prep
mkdir -p $RPM_BUILD_ROOT/$ST_TOOL_PATH/TCC_Releases/Other/OSS/linux-glibc2.3-amd64
cp -r $ST_TOOL_PATH/TCC_Releases/Other/OSS/linux-glibc2.3-amd64/8.6.1 $RPM_BUILD_ROOT/$ST_TOOL_PATH/TCC_Releases/Other/OSS/linux-glibc2.3-amd64

%clean
%{__rm} -rf %{buildroot}

%files 
%defattr(755,root,root)
"%{prefix}/TCC_Releases"
