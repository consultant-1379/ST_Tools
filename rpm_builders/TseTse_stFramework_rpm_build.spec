Summary: TseTse_stFramework
Name: tsetse_stframework
Version: 5.11
Release: 3
License: Ericsson
Group: --
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /opt/hss/system_test
BuildArch: noarch

%description
Automation framework for HSS testing

%prep
mkdir -p $RPM_BUILD_ROOT/$ST_TOOL_PATH
cp -r $GIT_PATH/ST_Tools/Automation $RPM_BUILD_ROOT/$ST_TOOL_PATH

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(755,root,root)
"%{prefix}/Automation"
