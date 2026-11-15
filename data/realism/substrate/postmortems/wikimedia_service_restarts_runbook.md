---
source: https://wikitech.wikimedia.org/wiki/Service_restarts
retrieved: 2026-11-15
license: CC BY-SA 4.0 (Wikimedia wikitech)
---

From Wikitech

This page collects procedures to restart services (or reboot the underlying server) in the WMF production cluster.

## acmechief hosts

Every server running the acme_chief::cert class profile will fail to run Puppet while the servers are down. To avoid Puppet spam you can disable Puppet on the hosts during reboots (apart from the Puppet spam there's no errors caused by the temporary non-availability of the acmechief servers):

sudo cumin 'R:acme_chief::cert' "disable-puppet 'acmechief maintenance - ${USER}'"

After rebooting you need to rearm the keyholder:

sudo keyholder arm

(The password is in pwstore.)

## aqs

aqs* hosts are simply Cassandra hosts. "AQS" as a service is in fact a series of Kubernetes services that can be restarted using the standard Kuberenetes procedure.

Cassandra needs to be roll restarted one node at the time, see the section about Cassandra in this page.

## ATS

The ats-backend-restart script is installed on all ATS nodes and takes care of depooling the service, restarting it, and repooling. If trafficserver needs to be restarted on a single host, just run the script as root. Cluster-wide rolling restarts can be performed with cumin, see the following example:

sudo cumin -b1 -s30 A:cp-codfw ats-backend-restart

Be aware that ats-backend-restart also sleeps for some 60 seconds so the cumin command will take over an hour. however the ATS cache_upload and cache_text servers can be restarted in parallel as can different datacenters

## Bacula

Before rebooting a storage host or the director make sure no backup run is currently in progress. This can be checked on helium via:

 sudo bconsole
 status director

## Bastions

To reboot those, it's best to announce the reboots in advance via the ops list, so that people are aware and no critical work is disrupted. There might still be people who overlook or forget it, so it's best to ping logged-in, non-idle users on IRC before proceeding with the reboots.

## Cache proxies (varnish) (cp)

The Varnish servers will depool themselves on clean shutdown.

Alternatively you can run the depool and pool commands as root.

Or also:confctl select 'name=<fqdn>' set/pooled=yes On puppetmaster1001 as root.

<fqdn> can be a regex if tackling several machines, change yes to no for a depool.

When restarting nginx

 cumin 'foo*' -b 1 -s 15 'service nginx upgrade'

performs a graceful online restart with 15 second delay in between.

When restarting Varnishkafka

systemctl restart varnishkafka-webrequest

Important note: restarting Varnishkafka means that its sequence number internal variable is set to 0, affecting the JSON messages/event sent to Kafka (they all carry that field). This is usually not a big problem but if all the caching hosts are restarted in once it may cause alarms to Analytics for inconsistent data in Hadoop (hours after the restarts). Please do the restarts in small batches and alert the Analytics team in advance.

sudo cumin -s5 -b3 'C:varnishkafka' 'systemctl restart varnishkafka-webrequest.servicee'

## Cassandra (as used in aqs, sessionstore and restbase)

Cassandra as used in restbase/sessionstore uses a multi-instance setup, i.e. one host runs multiple Cassandra processes, typically named "a", "b", etc. For each instance there is a corresponding nodetool-NAME binary that can be used, e.g nodetool-a status -r.

A restart of cassandra as used for restbase does not require a depooling of the server (restbase will pick a different cassandra node if the local one is unavailable).

Before starting with a reboot/restart, check whether there are ongoing maintenance tasks (e.g. with Eric Evans).

The restart of the Cassandra instances can be performed using the c-foreach-restart command, it figures out how many instances are running and proceeds step by step:

 sudo c-foreach-restart --delay 10 --attempts 20 --retry 12

If you want to reboot a Cassandra server, the instances can be drained using c-foreach-nt, after the instances are drained, the server can be restarted:

 sudo c-foreach-nt drain

Before proceeding with the next node (both for restarts and reboots), ensure the restarted node has correctly rejoined the cluster (the name of the tool is relative to the restarted service instance):

 c-any-nt status -r

Note: The c-foreach-restart utility ensures that restarted nodes are fully online before continuing; This should not be necessary when using c-foreach-restart.

Directly after the restart the tool might throw either an exception reading "No nodes are present in the cluster" or another reading "Failed to connect to 'localhost:7189'" but this usually sorts out within a few seconds. If the node has correctly rejoined the cluster, it should be listed with "UN" prefix, e.g.:

UN  xenon-a.eqiad.wmnet              224.65 GB  256     ?       0d691414-4132-4854-a00d-1d2671e15728  rack1

## Ceph (WMCS CloudVPS)

The Ceph storage cluster is a critical component of CloudVPS. Any action on these service should be coordinated with the WMCS team either through IRC or Phabricator.

Detailed information on restarting Ceph services (should be handled by the WMCS team)

## ChartMuseum

See ChartMuseum#Operations

## cloudcontrol

nova-{api,conductor,scheduler}, neutron-server, keystone-all and glance-{api,registry} are all part of OpenStack and are very disruptive to restart.  restarts to theses services are only preformed for serious updates and are generally bundled with a reboot or the server.

Any action should be coordinated with the WMCS team and communicated to WMCS users

## clouddb (Wikireplicas)

These are Mariadb servers, but they have a peculiar failover setup on haproxy.

- Depool using the hiera method described in WMCS docs. The docs for the legacy wikireplicas (named labsdb1*) are also on that page.

- Wait for queries to finish or kill queries as needed on the instance

- Stop replication. On a legacy wikireplica (labsdb*) run sudo -i mysql -e "STOP SLAVE". On the clouddb* wikireplicas, you need to connect using the appropriate socket (such as sudo -i mysql -e "STOP SLAVE" -S /var/run/mysqld/mysqld.s1.sock for the s1 instance).

- Stop the server, if labsdb systemctl stop mariadb or stop both instances, if a clouddb, ie. systemctl stop mariadb@s1 and systemctl stop mariadb@s3 then reboot

- When it comes back up start mariadb and then make sure you sudo -i mysql -e "START SLAVE" (on labsdb) or the same with the appropriate sockets (clouddb) and make sure that SHOW SLAVE STATUS\G looks healthy

## Charon

Charon is used for ipsec you can sudo depool; sudo systemctl restart ipsec.service ; sudo pool do one at a time

## Cumin

For reboots make sure noone is currently using the host. After a reboot, the keyholder needs to be rearmed:

 sudo keyholder arm

(The passphrase is in pwstore in the cumin-master-key-passphrase file).

## Druid

Druid is used for the Analytics/Data_Lake.  There are two druid clusters:

- druid analytics - serves queries for Analytics UIs (Turnilo/Superset/etc..)

- druid public - serves queries for the public AQS service

If Druid analytics goes down, the Analytics team will notice, and some Hadoop jobs may fail, but no real world service will be impacted. If Druid public goes down, API queries to AQS may fail since part of the API needs to fetch content from Druid (Mediawiki edit history related queries).

Please note two important things:

- Zookeeper is running on the Druid hosts (used by the Druid daemons).

- Turnilo (turnilo.wikimedia.org) and Superset (superset.wikimedia.org) uses Druid analytics as backend storage to show data.

To roll restart Druid daemons use the related cookbook:

$ sudo cookbook sre.druid.roll-restart-workers public

$ sudo cookbook sre.druid.roll-restart-workers analytics

Also see: Analytics/Cluster/Druid#Full Restart of services

## Authoritative DNS

     sudo confctl select 'name=<dns-host-FQDN>' set/pooled=no

To depool individual services, specify the service name:

     sudo confctl select 'name=<dns-host-FQDN>,service=authdns-ns0' set/pooled=no

## DNS recursors

Rebooting the servers will cause some currently unavoidable BGP alerts, e.g. for a reboot in eqsin, simply give a headsup in #wikimedia-operations before you start:

PROBLEM - BGP status on cr2-eqsin is CRITICAL: BGP CRITICAL - AS64605/IPv4: Active - Anycast https://wikitech.wikimedia.org/wiki/Network_monitoring%23BGP_status
PROBLEM - BFD status on cr2-eqsin is CRITICAL: CRIT: Down: 1 https://wikitech.wikimedia.org/wiki/Network_monitoring%23BFD_status
PROBLEM - BGP status on cr3-eqsin is CRITICAL: BGP CRITICAL - AS64605/IPv4: Active - Anycast https://wikitech.wikimedia.org/wiki/Network_monitoring%23BGP_status

Auth DNS and rec DNS are on the same hosts, so follow the same instructions above.

## Docker-registry

depool server, systemctl restart docker-registry; systemctl restart nginx; pool.

## Elasticsearch

The cluster continues to work fine as long as elasticsearch is only restarted on one node at a time (or the host rebooted). The overall cluster state can be queried from any node.

On an arbitrary elasticsearch node the following command returns the overall state of the elasticsearch cluster:

 curl -s localhost:9200/_cluster/health?pretty

Initially the "status" field should be "green". After elasticsearch has been stopped/rebooted, the "number_of_nodes" will go down by one and the "status" will switch to "yellow". The search cluster will resync, but it might take awhile hours to reach that state. Once it has recovered that next node can be restarted/rebooted. See search cluster administration for more details about elasticsearch administration.

### Disgusting script to view Elasticsearch cluster health

Apologies in advance, but you can use es-maint-viewer.sh to view cluster health during a maintenance operation. Run the script from a cumin host and it will open several tmux windows to measure the health of all Elastic clusters in the DC (there are two small and one large clusters per DC).

### Restart Procedure

For cluster-wide restarts, reboots, or upgrades,  use the rolling-operation cookbook.

### Node ban procedure (for DC maintenances)

To ban specific Elastic nodes from the cluster (such as for DC maintenances), use the node ban cookbook

## etcd

Please note that the one etcd cluster is replicated via etcdmirror to the other one, and failing to replicate means paging people. The following hiera variable indicates what is the instance that is running etcdmirror (at the moment conf1005):

profile::etcd::replication::active: true

Etcdmirror reads from the one datacenter and replicates its data to the etcd cluster in the other. This means that if you reboot the hosts in the master cluster (currently codfw) you need to downtime the etcdmirror service on the server in the slave cluster doing the replication, or that will page.

Log on the server that is replicating and check what is the source host for the replication:

elukey@conf2002:~$ sudo systemctl status etcdmirror-conftool-eqiad-wmnet.service
● etcdmirror-conftool-eqiad-wmnet.service - Etcd mirrormaker
   Loaded: loaded (/lib/systemd/system/etcdmirror-conftool-eqiad-wmnet.service; enabled)
   Active: active (running) since Mon 2017-07-17 14:52:18 UTC; 55min ago
 Main PID: 23540 (etcd-mirror)
   CGroup: /system.slice/etcdmirror-conftool-eqiad-wmnet.service
           └─23540 /usr/bin/python /usr/bin/etcd-mirror --strip --src-prefix /conftool --dst-prefix /conftool https://conf1001.eqiad.wmnet:2379 http://localhost:2378

In this case etcdmirror on conf2002 is pulling data from conf1001.

The etcd nodes are internal clustered and can be rebooted one at a time, or the etcd service can be restarted one host at a time with sudo systemctl restart etcd.service.

After a reboot, the cluster health can be checked via one of the following:

sudo etcdctl -C https://$(hostname -f):2379 cluster-health

 /usr/local/bin/nrpe_etcd_cluster_health --url https://conf1001.eqiad.wmnet:2379

Whenever you reboot/restart any etcd host please verify that etcdmirror is active and not issuing errors in its logs afterwards.

Whenever you reboot/restart any etcd host please verify with Traffic that Pybal is happy and working correctly - T169765

This can often be resolved by running sudo systemctl restart pybal.service on the alerting lvs server.  however make sure you leave time between restarts to ensure ALL BGP sessions in pybal have re-established before restarting a different daemon

check the notes about Zookeeper since it is co-hosted on the conf* hosts.

More in depth info about the etcd cluster can be found in Etcd#Operations

## Exim

The exim service/the mx* hosts can be restarted/rebooted individually without external impact; mail servers trying to deliver mails will simply re-try at a later point if the SMTP service is unavailable:

service exim4 restart

## Event Schema Service

schema.svc.$site.wmnet is hosted on the schema* servers.  This service is a very simple nginx http file server that allows for remote http requests for schemas cloned from git repositories.  Rebooting these servers just requires the usual rolling depool; reboot; pool for each.

## failoid

Failoid is used for DNS discovery to indicate that a service is failing. It's iptables setup rejects a connection immediately instead of letting the client run into a timeout. As such, Failoid instances can be rebooted one at a time unless there's currently an ongoing service outage.

## Ganeti

Ganeti nodes can be upgraded without impact on the running VMs. To reboot a node, its virtual machines nodes need to be migrated to other hosts, with the master node needing special attention.

## Gerrit

The restart should be pre-announced on #wikimedia-operations (for maybe 15 minutes) to give people a heads-up:

service gerrit restart

## GitLab

The restart should be pre-announced on #wikimedia-gitlab (for maybe 15 minutes) to give people a heads-up. To restart all GitLab components run:

gitlab-ctl restart

GitLab needs some time to recover and answers with 5XX for some minutes. It is also possible to restart individual components of GitLab using gitlab-ctl restart nginx. Get a list of all services using gitlab-ctl status.

The GitLab SSH daemon can be restarted using:

systemctl restart ssh-gitlab

### GitLab runners

GitLab runners are separate from GitLab servers and, unlike servers, can be rebooted anytime. Use the cookbook sre.gitlab.reboot-runner to gracefully reboot Runners.

To restart gitlab-runner process:

systemctl restart gitlab-runner

They exist both in production and in cloud.

See also GitLab Cheat Sheet.

## Hadoop workers

Please coordinate with the Analytics team before taking any action, there are multiple dependencies to consider before proceeding. For example, Gobblin might need to be stopped to prevent data loss/lag in HDFS.

Hadoop's master node (an-master1001.eqiad.wmnet) and its standby replica (an-master1002.eqiad.wmnet) are configured for automatic failover, but please read the following page: Analytics/Cluster/Hadoop/Administration#Manual Failover

Three of the Hadoop workers run an additional JournalNode process to ensure that the standby master node is kept in sync with the active one. These are configured in the puppet manifest. When rebooting JournalNode hosts it must be ensured that two additional JournalNode hosts are up and running.

systemctl restart hadoop-hdfs-journalnode

The other Hadoop workers are running two services (hadoop-hdfs-datanode and hadoop-yarn-nodemanager). The services on the Hadoop workers should be restarted in this order:

systemctl restart hadoop-yarn-nodemanager
systemctl restart hadoop-hdfs-datanode

The service restarts have no user-visible impact (and the machines can also be rebooted). It's best to wait a few minutes before proceeding with the next node.

The Yarn node managers support graceful reload, so all the Yarn containers running on the same node are not killed/restarted at the same time (the node manager dumps its state on disk and it is able to restore its config and running containers while starting). This means that until a container finishes, new package upgrades like open-jdk ones, will not be picked up and will show up in commands like lsof.

There is now a cumin cookbook to restart all the Hadoop workers (the master nodes are delicate and need to be done manually):

$ sudo cookbook sre.hadoop.roll-restart-workers --hdfs-dn-sleep-seconds 120 --hdfs-jn-sleep-seconds 120 analytics

## HAProxy

Please check the DNS section to depool servers on at a time before restarting haproxy on DNS servers

HAProxy servers are used for routing misc servers. They are currently a SPOF, so if you need to restart them, make sure they are not in use by using a different proxy.

HAProxy configuration can be reloaded without stopping it. However, HAProxy need explicit configuration of the files used for config. If the name or number of files change (not only the contents itself), reload doesn't work, and it requires a full service restart.

## Hive

The Apache Hive data warehouse software facilitates reading, writing, and managing large datasets residing in distributed storage using SQL. Since it is not a stateless service, please contact the Analytics team before restarting it to pause to avoid any failure in the Hadoop cluster. It is composed by two daemons, the server and the metastore.

On an-coord1001:

$ systemctl restart hive-server2

$ systemctl restart hive-metastore

## Icinga

Icinga is externally monitored by a custom script. To downtime the external meta-monitoring:

- Log in to HetrixTools (credentials in pwstore).

- Navigate to "Uptime Monitors".

- Select (check the box on the left of) "wmf - metamonitoring - icinga - extmon - VIP".

- From the dropdown menu, select "Maintenance Mode (without notifications)".

Once the restart has completed, select "End Maintenance Mode".

The passive Icinga server is not monitored, so a manual check to ensure that all services are running is required. Keyholder must also be re-armed (in case of a reboot).

## IDP

When rebooting the servers first ensure you update DNS so the record for idp.wikimedia.,org is pointing to the correct address (the one not beeing rebooted) and wait for 5 mins for the TTL to expire.

## Kafka brokers (analytics)

Several consumers might get upset by metadata changes due to broker restarts, please make sure that the Analytics team is alerted beforehand:

- EventLogging

- Graphite#statsv (running on hafnium)

One Kafka broker can be restarted/rebooted at a time:

service kafka restart

It needs to be ensured that all replicas are fully replicated.
After restarting a broker a replica election should be performed.

Restarting a broker will trigger a bug in the Kafka 0.9 truncate log function that will set all the logs' mtime to now (more info https://phabricator.wikimedia.org/T136690). This will mess up the regular Kafka cleaning policy that we have set, namely remove all the files with mtime older than 7 days. This could lead to excessive data stored in one disk partition and disk full alarms. To avoid this, the Analytics team deployed a limit for the total topic partition size (500GiB), so even in case of restarts we should be ok. Just alert the Analytics team on IRC to give them a heads up.

## Kafka brokers (main clusters)

kafka-main100[123] and kafka-main200[123] were running also the EventBus service (EventBus/Administration) but now they are not.

Please sync with the Services team to coordinate the restart/reboot of kafka-main[123]00[123], since they might need to temporarily watch services like ChangeProp.

To roll restart Kafka daemons on them:

sudo cookbook sre.kafka.roll-restart-brokers main-eqiad

sudo cookbook sre.kafka.roll-restart-brokers main-codfw

## Kubernetes masters

They are behind LVS so standard depool/repool methods.

## Kubernetes workers

Further information can be found here: Kubernetes#Administration

## Logstash

After rebooting a Logstash node running Elasticsearch (1004-1006), it needs to be waited until the cluster state has recovered to "green" (see the "Elasticsearch" section for details).
1001 to 1003 and 1007 to 1009 run Logstash, Kibana (Apache proxied via Varnish) and a data-less Elasticsearch node. The multiple logstash endpoints are behind LVS. They can also be rebooted/restarted one at a time after depooling them, from experience it could take ~5 min for logstash to listen again on its ports so allow enough time between (de)pools.

## LVS

The LVS servers are configured in primary/backup pairs (configured on the routers and visible in puppet in modules/lvs/manifests/configuration.pp). To redirect the traffic from a primary to the backup, pybal can be stopped (traffic is then being redirected to the backup). Before stopping Pybal, make sure to disable Puppet first as a Puppet run might enable it.

## maps

Kartotherian runs on Kubernetes and can follow the standard Kubernetes service restart procedure. Restarts of postgres on the master require puppet to be disabled and the imposm service stopped beforehand.

## Mcrouter

the mcrouter service can be restarted as long as the server has been depooled e.g.

sudo depool; sleep 5 ; sudo systemctl restart mcrouter ; sleep 5; sudo pool

## MySQL/MariaDB

By Default mysql is not configured to start after a reboot so must be started manuly

Long running queries from mwmaint1001 maintenance, SPOF in certain mysql services (masters, specialized slave roles, etc.) prevent from easy restarts.

The procedure is, for a core production slave:

- Depool from mediawiki

- Wait for queries to finish

- Stop replication mysql -e "STOP SLAVE"

- Stop the server, /etc/init.d/mysql stop then reboot

For a core production master:

- Failover to another server first (which is not easy)

For a misc server:

- Failover using HAProxy (dbproxy1***)

- Some services need a reload due to long-running connections or persistent connections. This is documented on: MariaDB/misc

For wikireplicas servers look up at Service_restarts#clouddb_(Wikireplicas)

More info on ways to speed up this at MariaDB and MariaDB/troubleshooting

## Memcached

Memcached is used as caching layer for MediaWiki and it is co-hosted with Redis on mcXXXX machines (eqiad and codfw). MediaWiki uses nutcracker (https://github.com/twitter/twemproxy) to abstract the connection to the memcached cluster with one local socket and to avoid "manual" data partitioning.

Restarting the service is very easy but please remember that the cache is only in memory and it is not persisted on disk before restarts. Direct consequences of a restart might be:

- errors logged in https://logstash.wikimedia.org/#/dashboard/elasticsearch/memcached

- errors logged in https://logstash.wikimedia.org/#/dashboard/elasticsearch/hhvm

A complete restart of the memcached cluster must be coordinated carefully with SRE and MediaWiki Engineering teams to establish a good procedure to avoid performance hits. If you need to stop memcached for a long maintenance (e.g. OS re-install, etc..) please remove the related host from Heira first (example https://gerrit.wikimedia.org/r/#/c/273430/).

If you want to rapidly check if memcached is working after a restart or an upgrade:

mc1008:~$ echo stats | nc localhost 11211

cmd_set, cmd_get, total_items and current_items should show values greater than zero (increasing over time). This is not exhaustive of course!

Please remember that memcached on mcXXXX hosts is co-hosted with Redis, read carefully its section on this page if you need to operate on the whole host rather than only memcached:

Redis is running with a special service name to allow its use as multi-instance (several Redis processes on the same node).

sudo service redis-instance-tcp_6379 restart

It is used in various places for different tasks like:

- Storage of user sessions on mcXXXX hosts (co-hosted with Memcached)

- Queue for Job tasks on rdbXXXX hosts

Restarting Redis is generally a safe operation since the daemon persists its data to disk before restarting (unlike Memcached). Please note that if you need to perform a complete stop of the service (e.g. OS re-install, etc..) you will need to depool the related host from service first (example https://gerrit.wikimedia.org/r/#/c/273430/). Useful references:

- https://phabricator.wikimedia.org/T123675 (Reinstall redis servers (Job queues) with Jessie)

- https://phabricator.wikimedia.org/T123711 (Reinstall eqiad memcache servers with Jessie)

Please note the removing a mcXXXX host from the Redis pool will cause user sessions to be dropped. This is unavoidable since each mcXXXX host holds a partition of the sessions not replicated elsewhere (this will not be true when codfw replication will be fully working, but hopefully this page will be already updated). Please carefully plan a complete cluster maintenance to avoid a massive loss of user session in a short time window. Please also inform Wikitech Ambassadors (https://lists.wikimedia.org/pipermail/wikitech-ambassadors/) and the performance team with one day of advance.

Puppet will take time to rollout a change like de-pooling a Redis host from its pool because it won't update all the hosts at once. This means that it usually takes ~30 minutes for all the connections to drain from a host. In this timeframe you will see errors in logstash. Please also make sure that all the client connections drop to zero before operating on the host (rebooting, re-installing the OS, etc..) using commands like:

redis-cli -a "$(sudo grep -Po '(?<=masterauth ).*' /etc/redis/tcp_6379.conf)" client list | wc -l
redis-cli -a "$(sudo grep -Po '(?<=masterauth ).*' /etc/redis/tcp_6379.conf)" monitor

### memcached on other services

- graphite uses memcached to cache queries, it's safe to upgrade.

- swift frontend servers use memcached to cache lookups for container/account existence and auth tokens. It's safe to upgrade, but the frontend servers should be depooled for the restart.

## ncredir

ncredir is working in active/active mode, so to roll-restart you have to depool and repool in sequence. For example:

 confctl select name=ncredir2001.codfw.wmnet set/pooled=no
 ... reboot
 confctl select name=ncredir2001.codfw.wmnet set/pooled=yes

To get the current status:

 # confctl select 'cluster=ncredir' get
{"ncredir2002.codfw.wmnet": {"pooled": "yes", "weight": 10}, "tags": "dc=codfw,cluster=ncredir,service=nginx"}
{"ncredir2001.codfw.wmnet": {"pooled": "yes", "weight": 10}, "tags": "dc=codfw,cluster=ncredir,service=nginx"}
{"ncredir1001.eqiad.wmnet": {"pooled": "yes", "weight": 10}, "tags": "dc=eqiad,cluster=ncredir,service=nginx"}
{"ncredir1002.eqiad.wmnet": {"pooled": "yes", "weight": 10}, "tags": "dc=eqiad,cluster=ncredir,service=nginx"}

You can also use the restart-nginx script provided by profile::lvs::realserver to restart nginx safely:

vgutierrez@ncredir5001:~$ sudo -i restart-nginx
2022-03-18 11:34:27,945 [INFO] Depooling currently pooled services
2022-03-18 11:34:28,435 [INFO] Waiting 3 seconds before restarting the service...
2022-03-18 11:34:31,439 [INFO] Restarting the service
2022-03-18 11:34:31,522 [INFO] Repooling previously pooled services

## netflow

These hosts can be rebooted anytime unless there's currently on incident ongoing.

## Netmon

After a reboot, the keyholder needs to be rearmed:

 sudo keyholder arm

(The passphrase is in pwstore in the rancid-key-passphrase file).

## ntpd

We run four ntpd servers (chromium, hydrogen, acamar, achenar) and all of these are configured for use by the other servers in the cluster. As such, as long as only one server is restarted/rebooted at at time, everything is fine. The ntpd running locally on the individual servers can easily be restarted at any any time.

## Oozie

Oozie is a workflow scheduler system to manage Apache Hadoop jobs written in Java. Since it is not a stateless service, please contact the Analytics team before restarting it to pause its Bundles/Coordinators/Workflows to avoid any failure in the Hadoop cluster.

On an-coord1001:

$ sudo systemctl restart oozie

## Ores

Standard depool/repool mode for reboots. For service restarts to pick up e.g. a new library, the services uwsgi-ores.service and celery-ores-worker.service need to be restarted.

## openldap

We run two openldap installations (the oit mirror and for labs). Both are using mirrormode replication and the respective clients (mails servers for oit mirror and (primarily) labs instances for openldap-labs). The openldap servers (or the slapd process) can be rebooted/restarted one at a time, the clients will transparently try to reconnect to the other host of the respective cluster. The number of connected clients are shown in grafana for openldap-labs.

## Parsoid

Parsoid has moved from JS to PHP. This means nowadays a parsoid restart equals a php-fpm restart. Use "restart-php7.2-fpm" via cumin. See Service_restarts#Application_servers_(also_image/video_scalers_and_job_runners)

## Phabricator

Phabricator runs on phabricator_active_server (look in hiera). To restart Phabricator php:

sudo systemctl restart php8.4-fpm.service

Phabricator also runs a background daemon manager called phd. To restart the daemon (for example for a new PHP version):

sudo systemctl restart phd.service

Phabricator also runs apach2 and envoy, to restart those:

sudo systemctl restart envoyproxy.service apache2.service

## ping

For each reboot, the routers need to temporary disable/redirect the ICMP redirection for the instance to boot.

## Pivot

Pivot is stateless and can be restarted at any time.

## Pool counters

The pool counters in the inactive data center can be rebooted rightaway. For the active data center, they should be removed/readded from mediawiki-config one by one (example commit: https://gerrit.wikimedia.org/r/#/c/418870/)

Before rebooting it can be doublechecked with "ss" (on port 7531) that no further mediawikis are connected. For more details, see the serviceops documentation.

## PKI

The pki-root* servers can simply be rebooted at any time

for pki* servers passive services can simply be rebooted.  The active server (the server pointed to via pki.discovery.wmnet.) will need updating in DNS first.  As this domain is only used internaly you can clear the DNS cache instead of waiting for the TTL to expire ( sudo cookbook sre.dns.wipe-cache pki.discovery.wmnet )

## Postgres

### puppetdb

Clients only talk to Java-based frontend processes, but during the postgres update puppet runs will fail, so follow the approach described for puppetdb reboots.

## Prometheus

Prometheus is ran in active/active mode, so to roll-restart you have to depool and repool in sequence. For example:

 confctl select name=<name>.codfw.wmnet set/pooled=no
 ... reboot
 confctl select name=<name>.codfw.wmnet set/pooled=yes

To get the current status:

 # confctl select service=prometheus get
 {"prometheus2003.codfw.wmnet": {"pooled": "yes", "weight": 10}, "tags":
 "dc=codfw,cluster=prometheus,service=prometheus"}
 {"prometheus2004.codfw.wmnet": {"pooled": "yes", "weight": 10}, "tags":
 "dc=codfw,cluster=prometheus,service=prometheus"}
 {"prometheus1003.eqiad.wmnet": {"pooled": "yes", "weight": 10}, "tags":
 "dc=eqiad,cluster=prometheus,service=prometheus"}
 {"prometheus1004.eqiad.wmnet": {"pooled": "yes", "weight": 10}, "tags":
 "dc=eqiad,cluster=prometheus,service=prometheus"}

The Prometheus servers in easms/ulsfo (running on bastions) are not redundant, when restarting/rebooting a temporary loss of metrics data is acceptable.

## puppetdb

Restarting the puppetdb.service and reboots of the instance will cause significant Puppet errors (about ~10% of all hosts), so it's best to disable Puppet/re-enable Puppet for the restart/reboot:

Disable Puppet

Enable Puppet

## Puppet masters

For short maintenance tasks (service restarts, reboots), it's best to disable Puppet temporarily, otherwise there'll be a shower of alerts.

For anything which takes a little longer (reimages, hardware maintenance by DC ops etc.), it's best to depool the puppet masters. This requires the following Puppet/DNS changes:

- For Puppet master backends (currently 1002/1002 and 2002), the backend server needs to be marked as offline, example commit: https://gerrit.wikimedia.org/r/#/c/operations/puppet/+/543142/

- For Puppet master frontends (currently 1001 and 2001), we need to consider which host currently hosts the Puppet CA. Both require a Puppet patch to uncomment/disable the config-master (example commit: https://gerrit.wikimedia.org/r/#/c/operations/puppet/+/543281/).

Frontends are found by Puppet clients via DNS resolution, so we need to redirect the (site-specific) CNAMEs to the other puppetmaster frontend (example commit: https://gerrit.wikimedia.org/r/#/c/operations/dns/+/543280/). If the server is taken down which currently holds the Puppet CA, we also need to fail that over to the other frontend (example commit: https://gerrit.wikimedia.org/r/#/c/operations/puppet/+/540392/)

## Puppetboard

Puppetboard service (puppetboard.wikimedia.org) is a python application that runs with uWSGI behind Apache2. It is configured as active/active at the traffic layer and is a completely stateless service, so each of its components can be restarted/rebooted anytime also because it is used only by the SRE team and is not a public service. In case of longer maintenance one host at a time can be depooled in the varnish director's hiera configuration.

## Redis

(Redis is also used on the memcached servers, please see that section for details.

### rdb* servers hosting the job queue for redis.

Redis is running with a special service name to allow its use as multi-instance (several Redis processes on the same node).

sudo systemctl restart redis-instance-tcp_6378
sudo systemctl restart redis-instance-tcp_6379
sudo systemctl restart redis-instance-tcp_6380
sudo systemctl restart redis-instance-tcp_6381

### oresrdb* servers

Theses servers can be restated with the following command.  however restarting will cayuse an outage as such you should create a ticket and liaise with the engineers responsible for the ores services

sudo systemctl restart redis-instance-tcp_6379
sudo systemctl restart redis-instance-tcp_6380

### mwlog* servers

sudo systemctl restart redis-instance-tcp_6379

Restarting Redis is generally a safe operation since the daemon persists its data to disk before restarting.

Putting redis entirely out of service for a long period, is a little more complex: The rdb hosts have a fallback slave (using the subsequent number), e.g. rdb1001 has rdb1002 as it's fallback. The fallback hosts can be rebooted without impact. For the time being (Jul 2019), Redis is used by changeprop and docker registry. It is safe to reboot reb* servers at any time. Do give a shout to service owners

## relforge

The relforge* cluster is very similar to the elastic* search clusters, but only consists of two hosts, so rebooting/restarting the master causes a service interruption (the service is only used internally), so #wikimedia-discovery should be notified. For the restart of relforge, replication should be stopped and both nodes rebooted at the same time:

 sudo systemctl restart elasticsearch_6@relforge-eqiad.service elasticsearch_6@relforge-eqiad-small-alpha.service

## restbase

The restbase service should be restarted one host at a time. Before restarting it, depool it with sudo depool-restbase. Repool it with sudo pool-restbase only once restbase is listening on it's external port again:

 ss -tl sport eq 7231

## RPKI

The RPKI servers can be restarted anytime for routine maintenance as long as there is at least one with all its Icinga checks green.

## stat* servers

Some users might have long-running scripts on those servers, in case of a reboot, it's best send a heads-up mail to analytics@lists.wikimedia.org a day ahead.

## sessionstore

These run a Casssandra cluster, see the section for details on restarts/reboots. Sessionstore queries are handled by a standard Kubernetes service Kask.

## Swift

In normal operation (and when restarting due to a spike in 5xx errors), the easiest way to restart the frontends is by using the sre.swift.roll-restart-reboot-swift-ms-proxies cookbook, which handles downtime, pybal, etc. for you. For example:

 sudo cookbook sre.swift.roll-restart-reboot-swift-ms-proxies --alias swift-fe-codfw --reason 'spike in 502s' restart_daemons

If that's not possible (e.g. during a serious enough incident that trying to downtime servers is unreliable), then read on.

Frontend servers (ms-fe*) should be depooled via pybal when making service restarts or reboots. Whether a server has been correctly depooled can be checked by tailing /var/log/swift/proxy-access.log.

Backend servers can simply be rebooted/restarted one at a time (with a 30 second delay in between when restarting); an unresponsive host is automatically handled by the frontend servers.

Backends service restarts
systemctl restart swift*

Frontends service restarts
systemctl restart swift-proxy

As an example, to restart the swift-proxy in codfw:

sudo cumin -b 1 -s 5 'A:codfw and P{O:swift::proxy}' 'depool && sleep 3 && systemctl restart swift-proxy && sleep 3 && pool'

## Thanos

Thanos has both a frontend and backend. For backends the same rules as Swift above apply. Ditto for frontends, except that there are two services for host: swift-proxy and thanos-query. For thanos-swift.discovery.wmnet and thanos-query.discovery.wmnet respectively. The sre.swift.roll-restart-reboot-swift-thanos-proxies cookbook is the easiest way to restart the frontend servers.

## Thumbor

Thumbor nodes can be restarted using the standard roll_restart process for Kubernetes services.

## Volunteer Response Team (VRTS/OTRS)

Service and server restarts should be annouced in IRC channel first (#wikimedia-vrt). Please note VRTS is also known as OTRS (old name) or znuny (ticket system).

### Service Restart

VRTS runs multiple services:

cron:

sudo systemctl restart cron.service

exim4 (email):

sudo systemctl restart exim4.service

apache2 (webserver):

sudo systemctl restart apache2.service

vrts-daemon (znuny ticket system):

sudo systemctl restart vrts-daemon.service

### Server Reboot

To reboot use the sre.hosts.reboot-single cookbook:

sudo cookbook sre.hosts.reboot-single otrs1001.eqiad.wmnet

## Wikidata Query Service (WDQS)

WDQS nodes can be restarted one at a time at any time. They must be depooled/pooled.

The following services are part of WDQS:

- wdqs-blazegraph

- wdqs-categories

- wdqs-updater

## Wikidough DoH/DoT Service

### Service Restart

Wikidough hosts: doh[123456]00[12]

Wikidough has two components, dnsdist and pdns-recursor. To restart,

sudo systemctl restart dnsdist.service
sudo systemctl restart pdns-recursor.service

Note that restarting the services clears the in-memory cache for both dnsdist and pdns-recursor.

### Server Reboot

As Wikidough is anycasted, the following steps need to be performed to depool a server:

- Disable Puppet on the host:

sudo disable-puppet "depooling host"

- Stop the bird service:

sudo systemctl stop bird.service

## Yubico authentication servers

The authentication servers can be rebooted one at a time. After each reboot the keystore on the YubiHSM needs to be unlocked using

 sudo yhsm-keystore-unlock

## Zookeeper

Zookeeper is used by Kafka and Hadoop for configuration management and leader election.

There are multiple clusters in Wikimedia:

- main eqiad (condf1004-6) - SRE cluster to support Kafka main eqiad and logging eqiad.

- main codfw (conf2001-3) - SRE cluster to support Kafka main codfw and logging codfw.

- analytics (an-conf1001-3) - Analytics cluster to support Hadoop.

- druid-public/analytics (druid1001-3, druid1004-6) - Analytics clusters to support Druid (co-located with the service).

Zookeeper nodes can be restarted one at a time via systemctl restart zookeeper. Once a node is restarted, before proceeding with the next one please verify its status using the following commands:

elukey@conf2001:~$ echo ruok | nc localhost 2181
imok

elukey@conf2001:~$ echo ruok | nc localhost 2181
imokelukey@conf2001:~$ echo stats | nc localhost 2181
Zookeeper version: 3.4.5--1, built on 05/31/2017 10:10 GMT
Clients:
[...]

Latency min/avg/max: 0/0/947
Received: 91891
Sent: 91894
Connections: 4
Outstanding: 0
Zxid: $someid
Mode: [follower|leader]
Node count: 1473

Please also verify that there is an active leader using Cumin:

elukey@cumin1001:~$ sudo cumin 'conf2*' 'echo stats | nc localhost 2181'

Please note that only executing "ruok" is not enough since it will only tell you what is the status of the daemon, not the health of the cluster! This caused Incident documentation/20170831-Zookeeper.

Please also double check https://grafana.wikimedia.org/d/000000261/zookeeper after each restart.

There is also a cumin cookbook:

$ sudo cookbook sre.zookeeper.roll-restart-zookeeper analytics

## Zuul

See instructions at mediawiki.org/CI

## One-off hosts

### sodium

Package installations/upgrades will fail, so this needs to be announced briefly ahead.

Retrieved from "https://wikitech.wikimedia.org/w/index.php?title=Service_restarts&oldid=2474223"

Categories:
- Services
- How-To
