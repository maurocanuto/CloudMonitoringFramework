# Monitoring Framework

The monitoring-framework  is a metric collection framework developed at BSC. 
It gathers metrics additionally to the ones collected by gmond or Host sFlow, and injects them to gmond using gmetric. In this sense, it plays a similar role as Host sFlow. It collects hardware performance events counters (host and VM level), raw performance events counters (host and VM level), usage per core and power metrics from several sources and sensors. It can also collect additional metrics that depend on the sensor availability in each server, like temperature metrics. It has been implemented in Python, and invokes external programs or uses available Python libraries to capture these additional metrics.
The performance and raw performance event counters are collected by means of perf, a profiler tool supported by Linux 2.6+ based systems. The perf tool can measure events coming from different sources such as pure kernel counters (context-switches, minor-fault, etc.) and micro-architectural events (number of cpu cycles, instructions retired, level 1 cache misses, last level cache misses, etc.). The raw performance event counters  are additional CPU counters that perf does not list out-of-the-box as named counters. Examples of them are the number of integer or floating point operations executed. To capture them, its hexadecimal code needs to be find out using perfmon2/libpfm (described later) and supplied to perf to capture them.

-----------------------------
========= Requirements ==========
-----------------------------

sudo apt-get install linux-tools-common  lm-sensors  python-dev flex bison wget python-pip python-guestfs;
sudo pip install pexpect;
sudo easy_install pysnmp;
sudo pip install psutil

- Install pexpect:
	sudo pip install pexpect

- Counters monitoring: perf
	Check if perf version support the command 'perf kvm stat ...'
	If it does not, download and install a newer version and set the path in the configuration file:
	E.g.:
		sudo apt-get install flex bison
		wget http://ftp.de.debian.org/debian/pool/main/l/linux-tools/linux-tools_3.13.6.orig.tar.xz
		tar xvf linux-tools_3.13.6.orig.tar.xz
		cd linux-tools-3.13.6/tools/perf/
		make
		Set perf_tool in the configuration file
	
- SNMP for Power metrics: PySNMP
	easy_install pysnmp

- Temperature metrics: lm-sensors and PySensors

	wget https://pypi.python.org/packages/source/P/PySensors/PySensors-0.0.2.tar.gz
	tar xvf PySensors-0.0.2.tar.gz
	cd PySensors-0.0.2/
	sudo python setup.py install

- CPU-Core Load 

sudo apt-get install python-dev
sudo pip install psutil

- Wattsup Power Metering 

sudo apt-get install python-pexpect


-----------------------------
========= Configuration ==========
-----------------------------

The file extraMetrics.conf is the configuration file for the monitoring system:

'yes' or 'no' if you want or not to monitor the following subsystems: vm_metrics, vm_counters, vm_raw_counters, host_counters, host_raw_counters, temperature_metrics, power_metrics
If you want to monitor vm_metrics (VM memory, cache and swap usage) you need to set 'vm_file_path' to the path of the file within the VM that stores those information.
Set 'metrics_config_path' to the file containing the metrics configuration (metrics.conf).

-----------------------------
  perf Raw Counters 

(http://www.bnikolic.co.uk/blog/hpc-prof-events.html)
(http://www.bnikolic.co.uk/blog/hpc-howto-measure-flops.html)

- Get the latest version of perfmon2/libpfm (h/t this developerworks article):

git clone git://perfmon2.git.sourceforge.net/gitroot/perfmon2/libpfm4
cd libpfm4
make
Run the showevtinfo program (in examples subdirectory) to get a list of all available events, and the masks and modifiers that are supported (see the output below for an example of the full output)

- Figure out what events and what with masks and modifiers you want to use. The masks are prefixed by Umask and are given as hexadecimal numbers and also symbolic names in the square brackets. The modifiers are prefixed by Modif and their names are also in square brackets.

- Use the check_events program (also in examples sub-directory) to convert the event, umask and modifiers into a raw code. You can do this by running the command as:

check_events <event name>:<umask>[(:modifers)*]
i.e., you supply the event name, the umask and multiple modifiers all separated by the colon character. The program will then print out, amongst other things, an raw event specification, for example:

Codes          : 0x531003
This hexadecimal code can be used as parameter to GNU.Linux perf tools, for example to perf stat by supplying it with -e r531003 option

-----------------------------
========= Execution ==========
-----------------------------

Launch the monitoring scripts:

	sudo ./start.sh

Stop the monitoring scripts:

	sudo ./stop.sh

Log:
	extraMetrics.log
