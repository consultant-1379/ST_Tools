Summary: TitanRuntimeGUI
Name: titan_runtime_gui
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
AutoReqProv: no

%description
Java aplication implementing GUI of HSS BAT

%prep
mkdir -p $RPM_BUILD_ROOT/$ST_TOOL_PATH/bin
cp -r $ST_TOOL_PATH/TCC_Releases/TitanSim_R5/Libraries/Runtime_GUI_CNL113437/bin/TitanRuntimeGUI.jar $RPM_BUILD_ROOT/$ST_TOOL_PATH/bin


%clean
%{__rm} -rf %{buildroot}

%files 
%defattr(755,root,root)
"%{prefix}/bin/TitanRuntimeGUI.jar"
