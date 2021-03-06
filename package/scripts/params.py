#!/usr/bin/env python
from resource_management import *
from resource_management.libraries.script.script import Script
import sys, os
from resource_management.libraries.functions.version import format_hdp_stack_version
from resource_management.libraries.functions.default import default
#from resource_management.libraries.functions import conf_select
#from resource_management.libraries.functions import hdp_select
#from resource_management.libraries.functions import get_kinit_path


def get_port_from_url(address):
  if not is_empty(address):
    return address.split(':')[-1]
  else:
    return address
    
# server configurations
config = Script.get_config()

zeppelin_dirname = 'incubator-zeppelin'

install_dir = config['configurations']['zeppelin-config']['zeppelin.install.dir']
download_prebuilt = config['configurations']['zeppelin-config']['zeppelin.download.prebuilt']
executor_mem = config['configurations']['zeppelin-config']['zeppelin.executor.mem']
stack_port = config['configurations']['zeppelin-config']['zeppelin.server.port']
spark_jar_dir = config['configurations']['zeppelin-config']['zeppelin.spark.jar.dir']
spark_jar = format("{spark_jar_dir}/zeppelin-spark-0.5.0-SNAPSHOT.jar")

zeppelin_user= config['configurations']['zeppelin-env']['zeppelin_user']
zeppelin_group= config['configurations']['zeppelin-env']['zeppelin_group']
zeppelin_log_dir = config['configurations']['zeppelin-env']['zeppelin_log_dir']
zeppelin_pid_dir = config['configurations']['zeppelin-env']['zeppelin_pid_dir']
zeppelin_log_file = os.path.join(zeppelin_log_dir,'zeppelin-setup.log')
zeppelin_hdfs_user_dir = format("/user/{zeppelin_user}")
  
zeppelin_dir = os.path.join(*[install_dir,zeppelin_dirname]) 
conf_dir = os.path.join(*[install_dir,zeppelin_dirname,'conf'])


#zeppelin-env.sh
zeppelin_env_content = config['configurations']['zeppelin-env']['content']

#detect HS2 details and java home
master_configs = config['clusterHostInfo']
hive_server_host = str(master_configs['hive_server_host'][0])
hive_metastore_host = str(master_configs['hive_metastore_host'][0])
hive_metastore_port = str(get_port_from_url(config['configurations']['hive-site']['hive.metastore.uris']))

java64_home = config['hostLevelParams']['java_home']



#e.g. 2.3
stack_version_unformatted = str(config['hostLevelParams']['stack_version'])

#e.g. 2.3.0.0
hdp_stack_version = format_hdp_stack_version(stack_version_unformatted)

if hasattr(Script, 'is_hdp_stack_greater_or_equal') and Script.is_hdp_stack_greater_or_equal("2.3"):
  mvn_spark_tag='spark-1.3'
else:
  mvn_spark_tag='spark-1.2'

#e.g. 2.3.0.0-2130
full_version = default("/commandParams/version", None)
hdp_version = full_version

if hasattr(functions, 'get_hdp_version'):
  spark_version = functions.get_hdp_version('spark-client')
