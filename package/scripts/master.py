import sys, os, pwd, grp, signal, time, glob
from resource_management import *
from subprocess import call


class Master(Script):
  def install(self, env):
    # Install packages listed in metainfo.xml
    self.install_packages(env)

    import params
    import status_params

    #location of prebuilt package from april 2015
    #snapshot_package='https://www.dropbox.com/s/nhv5j42qsybldh4/zeppelin-0.5.0-SNAPSHOT.tar.gz'
    #location of prebuilt package from June 14 2015
    snapshot_package='https://www.dropbox.com/s/s16oicpljugltjj/zeppelin-0.5.0-SNAPSHOT.tar.gz'
    
    #e.g. /var/lib/ambari-agent/cache/stacks/HDP/2.2/services/zeppelin-stack/package
    service_packagedir = os.path.realpath(__file__).split('/scripts')[0] 
            
    Execute('find '+service_packagedir+' -iname "*.sh" | xargs chmod +x')

    #Create user and group if they don't exist
    self.create_linux_user(params.zeppelin_user, params.zeppelin_group)
    self.create_hdfs_user(params.zeppelin_user, params.spark_jar_dir)
        
    #create the log dir if it not already present
    Directory([params.zeppelin_pid_dir, params.zeppelin_log_dir],
            owner=params.zeppelin_user,
            group=params.zeppelin_group,
            recursive=True
    )   
         
    Execute('touch ' +  params.zeppelin_log_file, user=params.zeppelin_user)    
    Execute('rm -rf ' + params.zeppelin_dir, ignore_failures=True)
    Execute('mkdir '+params.zeppelin_dir)
    Execute('chown -R ' + params.zeppelin_user + ':' + params.zeppelin_group + ' ' + params.zeppelin_dir)
    

    #Execute('echo master config dump: ' + str(', '.join(params.config['hostLevelParams'])))
    #Execute('echo stack_version_unformatted: ' + params.stack_version_unformatted)
    #Execute('echo hdp_stack_version: ' + params.hdp_stack_version)
    #Execute('echo spark_version: ' + params.spark_version)
    #Execute('echo full_version:' + params.full_version)

    #install maven as root
    Execute('curl -o /etc/yum.repos.d/epel-apache-maven.repo https://repos.fedorapeople.org/repos/dchen/apache-maven/epel-apache-maven.repo')
    Execute('yum -y install apache-maven >> ' + params.zeppelin_log_file)
    
    #depending on whether prebuilt option is selected, execute appropriate script
    if params.download_prebuilt:

      #Fetch and unzip snapshot build
      Execute('wget '+snapshot_package+' -O zeppelin.tar.gz -a '  + params.zeppelin_log_file, user=params.zeppelin_user)
      Execute('tar -zxvf zeppelin.tar.gz -C ' + params.zeppelin_dir + ' >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
      Execute('mv '+params.zeppelin_dir+'/*/* ' + params.zeppelin_dir, user=params.zeppelin_user)
      Execute('rm -rf zeppelin.tar.gz', user=params.zeppelin_user)
          
      
      #update the configs specified by user
      self.configure(env)

      
      #run setup_snapshot.sh in FIRSTLAUNCH mode
      Execute(service_packagedir + '/scripts/setup_snapshot.sh '+params.zeppelin_dir+' '+params.hive_server_host+' '+params.hive_metastore_host+' '+params.hive_metastore_port+' FIRSTLAUNCH ' + params.spark_jar + ' >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
      
    else:
      Execute('yum -y install java-1.7.0-openjdk-devel >> ' + params.zeppelin_log_file)
      if not os.path.exists('/root/.m2'):
        os.makedirs('/root/.m2')     
      Execute('cp '+service_packagedir+'/files/settings.xml /root/.m2/')
      
      Execute('cd '+params.install_dir+'; git clone https://github.com/apache/incubator-zeppelin >> ' + params.zeppelin_log_file)
      Execute('chown -R ' + params.zeppelin_user + ':' + params.zeppelin_group + ' ' + params.zeppelin_dir)

      #update the configs specified by user
      self.configure(env)
            
      Execute('cd '+params.zeppelin_dir+'; mvn -Phadoop-2.6 -Dhadoop.version=2.6.0 -P'+params.mvn_spark_tag+' -Pyarn clean package -DskipTests >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
            
      #run setup_snapshot.sh in FIRSTLAUNCH mode
      Execute(service_packagedir + '/scripts/setup_snapshot.sh '+params.zeppelin_dir+' '+params.hive_server_host+' '+params.hive_metastore_host+' '+params.hive_metastore_port+' FIRSTLAUNCH ' + params.spark_jar + ' >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
      
  def create_linux_user(self, user, group):
    try: pwd.getpwnam(user)
    except KeyError: Execute('useradd ' + user)
    try: grp.getgrnam(group)
    except KeyError: Execute('groupadd ' + group)

  def create_hdfs_user(self, user, spark_jar_dir):
    Execute('hadoop fs -mkdir -p /user/'+user, user='hdfs', ignore_failures=True)
    Execute('hadoop fs -chown ' + user + ' /user/'+user, user='hdfs')
    Execute('hadoop fs -chgrp ' + user + ' /user/'+user, user='hdfs')
    
    Execute('hadoop fs -mkdir -p '+spark_jar_dir, user='hdfs', ignore_failures=True)
    Execute('hadoop fs -chown ' + user + ' ' + spark_jar_dir, user='hdfs')
    Execute('hadoop fs -chgrp ' + user + ' ' + spark_jar_dir, user='hdfs')    

  

  def configure(self, env):
    import params
    import status_params
    env.set_params(params)
    env.set_params(status_params)
    
    #write out zeppelin-site.xml
    XmlConfig("zeppelin-site.xml",
            conf_dir = params.conf_dir,
            configurations = params.config['configurations']['zeppelin-config'],
            owner=params.zeppelin_user,
            group=params.zeppelin_group
    ) 
    #write out zeppelin-env.sh
    env_content=InlineTemplate(params.zeppelin_env_content)
    File(format("{params.conf_dir}/zeppelin-env.sh"), content=env_content, owner=params.zeppelin_user, group=params.zeppelin_group) # , mode=0777)    
    
    #run setup_snapshot.sh in configure mode to regenerate interpreter and add back version flags 
    service_packagedir = os.path.realpath(__file__).split('/scripts')[0]
    Execute(service_packagedir + '/scripts/setup_snapshot.sh '+params.zeppelin_dir+' '+params.hive_server_host+' '+params.hive_metastore_host+' '+params.hive_metastore_port+' CONFIGURE ' + params.spark_jar + ' >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
    

  def stop(self, env):
    import params
    import status_params    
    self.configure(env)
    Execute (params.zeppelin_dir+'/bin/zeppelin-daemon.sh stop >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
 
      
  def start(self, env):
    import params
    import status_params
    self.configure(env)    
    Execute (params.zeppelin_dir+'/bin/zeppelin-daemon.sh start >> ' + params.zeppelin_log_file, user=params.zeppelin_user)
    pidfile=glob.glob(status_params.zeppelin_pid_dir + '/zeppelin-'+params.zeppelin_user+'*.pid')[0]
    Execute('echo pid file is: ' + pidfile, user=params.zeppelin_user)
    contents = open(pidfile).read()
    Execute('echo pid is ' + contents, user=params.zeppelin_user)


  def status(self, env):
    import status_params
    #import params
    env.set_params(status_params) 

    
    #pid_file = glob.glob(status_params.zeppelin_piddir + '/zeppelin--*.pid')[0]
    #pid_file = glob.glob(status_params.zeppelin_pid_dir + '/zeppelin-zeppelin*.pid')[0]
    #pid_file='/var/run/zeppelin-notebook/zeppelin-zeppelin-sandbox.hortonworks.com.pid'
    pid_file = glob.glob(status_params.zeppelin_pid_dir + '/zeppelin-'+status_params.zeppelin_user+'*.pid')[0]

    check_process_status(pid_file)        

      
if __name__ == "__main__":
  Master().execute()
