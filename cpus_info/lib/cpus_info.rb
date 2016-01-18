# This class gives you information about the CPUs in your system.
# Each CPU socket contains cores. If hyperthreading is off, each core
# maps to a logical CPU. However, when hyperthreading is on, each core
# maps to 2 logical CPUs. The CPUs that you can see in Linux files
# such as /proc/cpuinfo, are logical CPUs.
# Using this class you can check how many logical CPUs, sockets,
# and cores a system has. Moreover, you can check whether
# hyperthreading is on. Also, you can check what sockets and cores
# are being used given a set of logical CPUs IDs.
# This has only been tested on Linux. It will not work on other OS.

class CpusInfo

    attr_accessor :logicalCpus, :logicalCpusInfo, :sockets, :cores, :hyperthreading

    def initialize
        # Get the number of logical CPUs
        @logicalCpus = `cat /proc/cpuinfo | grep processor | wc -l`.to_i

        # Get [socket_id, core_id] for each logical CPU
        @logicalCpusInfo = Array.new
        (0...@logicalCpus).each do |logicalCpuId|
            infoCpusRootDir = "/sys/devices/system/cpu/"
            infoCpuDir = "#{infoCpusRootDir}/cpu#{logicalCpuId}/topology/"
            socket_id = `cat #{infoCpuDir}/physical_package_id`.to_i
            core_id = `cat #{infoCpuDir}/core_id`.to_i
            @logicalCpusInfo.push([socket_id, core_id])
        end

        # Get the number of sockets
        @sockets = @logicalCpusInfo.each.collect { |logCpuInfo| logCpuInfo[0] }.uniq.count

        # Get the number of cores (number of sockets * distinct core IDs)
        coreIds = @logicalCpusInfo.each.collect { |logCpuInfo| logCpuInfo[1] }.uniq.count
        @cores = coreIds*sockets

        # Is hypethreading on?
        @hyperthreading = (@logicalCpus != @cores)
    end

    def getSocketAndCore(logicalCpuId)
        @logicalCpusInfo[logicalCpuId]
    end

    def getNumberOfSocketsUsed(logicalCpusIds)
        logicalCpusIds.collect { |logCpuId| @logicalCpusInfo[logCpuId][0] }.uniq.count
    end

    def getNumberOfCoresUsedWithHyperthreading(logicalCpusIds)
        logicalCpusIds.size - getNumberOfCoresUsed(logicalCpusIds)
    end

    def getNumberOfCoresUsedWithNoHyperthreading(logicalCpusIds)
        logicalCpusIds.size - 2*getNumberOfCoresUsedWithHyperthreading(logicalCpusIds)
    end

    def getNumberOfCoresUsed(logicalCpusIds)
        logicalCpusIds.collect { |logCpuId| @logicalCpusInfo[logCpuId] }.uniq.count
    end

end