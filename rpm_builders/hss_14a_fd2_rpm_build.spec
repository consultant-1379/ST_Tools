Summary: Population of hss_14a_fd2
Name: hss_14a_fd2
Version: 1.0
Release: 1
License: -
Group: Applications
Source: %{name}.tar.gz
BuildRoot:   %{_tmppath}/%{name}-%{version}-build
URL: http://www.ericsson.com
Distribution: SUSE Linux
Vendor: Ericsson
Prefix: /tsp/builds/system_test
BuildArch: noarch

%description
HSS population for PLM

%prep
mkdir -p $RPM_BUILD_ROOT%{prefix}
cp -r %{prefix}/%{name}_new $RPM_BUILD_ROOT%{prefix}

%clean
%{__rm} -rf %{buildroot}

%files 
%defattr(775,ECEMIT,seli-udm-hss)
"%{prefix}/%{name}_new"
