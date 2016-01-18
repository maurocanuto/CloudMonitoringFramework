Gem::Specification.new do |s|
  s.name        = 'cpus_info'
  s.version     = '0.1.0'
  s.date        = '2014-05-28'
  s.summary     = "A gem to get information about the CPUs of your system"
  s.author      = "David Ortiz"
  s.email       = 'david.ortiz@bsc.es'
  s.files       = ["lib/cpus_info.rb"]
  s.license     = 'LGPL-2.1'
  s.description = <<-EOF
    This class gives you information about the CPUs in your system.
    Each CPU socket contains cores. If hyperthreading is off, each core
    maps to a logical CPU. However, when hyperthreading is on, each core
    maps to 2 logical CPUs. The CPUs that you can see in Linux files
    such as /proc/cpuinfo, are logical CPUs.
    Using this class you can check how many logical CPUs, sockets,
    and cores a system has. Moreover, you can check whether
    hyperthreading is on. Also, you can check what sockets and cores
    are being used given a set of logical CPUs IDs.
    This has only been tested on Linux. It will not work on other OS.
  EOF
end