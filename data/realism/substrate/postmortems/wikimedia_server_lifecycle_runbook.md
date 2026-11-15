---
source: https://wikitech.wikimedia.org/wiki/Server_Lifecycle
retrieved: 2026-11-15
license: CC BY-SA 4.0 (Wikimedia wikitech)
---

From Wikitech

This page describes the lifecycle of Wikimedia servers, starting from the moment we acquire them and until the time we don't own them anymore. A server has various states that it goes through, with several steps that need to happen in each state. The goal is to standardize our processes for 99% of the servers we deploy or decommission and ensure that some necessary steps are taken for consistency, manageability & security reasons.

This assumes the handling of bare metal hardware servers, as it includes DCOps steps. While the general philosophy applies also to Virtual Machines in terms of steps handling and final status, check Ganeti#VM_operations for the usually simplified steps regarding VMs.

The inventory tool used is Netbox and each state change for a host is documented throughout this page.

## States

 | Server Lifecycle | Netbox
 | Racked
 | Power
 | In Puppet

 | requested | none, not yet in Netbox
 | no
 | n/a
 | no

 | spare | INVENTORY
 | yes or no
 | off
 | no

 | planned
 | PLANNED
 | yes or no
 | off
 | no

 | active | ACTIVE
 | yes
 | on
 | yes

 | failed | FAILED
 | yes
 | on or off
 | yes or no

 | decommissioned | DECOMMISSIONING
 | yes
 | on or off
 | no

 | unracked | OFFLINE
 | no
 | n/a
 | no

 | recycled | none, no longer in Netbox
 | no
 | n/a
 | no

The Netbox state STAGED is currently unused, see T320696 for the rationale.

## Server transitions

Diagram of the Server Lifecycle transitions. Source code available.

### Requested

- New hardware is requested for use via the instructions on the Phabricator Procurement Form.

- Hardware Allocation Tech will review request, and detail on ticket if we already have a system that meets these requirements, or if one must be ordered.

- If hardware is already available and request is approved by SRE management, system will be allocated, skipping the generation of quotes and ordering.

- If hardware must be ordered, the then DC Operations will gather quotes from our approved vendors & perform initial reviews on quote(s), working with the sub-team who requested the hardware.

#### Existing System Allocation

See the #Decommissioned -> Planned section below.

- Only existing systems (not new) use this step if they are requested.

- If a system must be ordered, please skip this section and proceed to Ordered section.

- Spare pool allocations are detailed on the #Procurement task identically to new orders.

- Task is escalated to DC operations manager for approval of spare pool systems.

- Once approved, the same steps of updating the procurement gsheet & filing a racking task occur from the DC operations person triaging Procurement.

#### Ordered

- Only new systems (not existing/reclaimed systems)

- Quotes are reviewed and selected, then escalated to either DC Operations Management or SRE Management (budget dependent) for order approvals.

- At the time of Phabricator order approval, a racking sub-task is created and our budget google sheets are updated.  DC Ops then places the approved Phabricator task into Coupa for ordering.

- Coupa approvals and ordering takes place.

- Ordering task is updated by Procurement Manager (Finance) and reassigned to the on-site person for DC Operations to receive (in Coupa) and rack the hardware.

- Racking task is followed by DC Operations and resolved.

#### Post Order

An installation/deployment task should be created (if it doesn't already exist) for the overall deployment of the system/OS/service & have the #sre and #DCOps tags. It can be created following the Phabricator Hardware Racking Request form.

### Requested -> Spare & Requested -> Planned

#### Receiving Systems On-Site

- Before the new hardware arrives on site, a shipment ticket must be placed to the datacenter to allow it to be received.

- If the shipment has a long enough lead time, the buyer should enter a ticket with the datacenter site.  Note sometimes the shipment lead times won't allow this & a shipment notification will instead be sent when shipment arrives.  In that event, the on-site technician should enter the receipt ticket with the datacenter vendor.

- New hardware arrives on site & datacenter vendor notifies us of shipment receipt.

- Packing slip for delivery should list an Phabricator # or PO # & the Phabricator racking task should have been created in the correct datacenter project at time of shipment arrival.

- Open boxes, compare box contents to packing slip.  Note on slip if correct or incorrect, scan packing slip and attach to ticket.

- Compare packing slip to order receipt in the Phabricator task, note results on Phabricator task.

- If any part of the order is incorrect, reply on Phabricator task with what is wrong, and escalate back to DC Ops Mgmt.

- If the entire order was correct, please note on the procurement ticket.  Unless the ticket states otherwise, it can be resolved by the receiving on-site technician at that time.

- Assign asset tag to system, enter system into Netbox immediately, even if not in rack location, with:

- Device role (dropdown), Manufacturer (dropdown), Device type (dropdown), Serial Number (OEM Serial number or Service tag), Asset tag, Site (dropdown), Platform (dropdown), Purchase date, Support expiry date, Procurement ticket (Phabricator or RT)

- For State and Name:

- If host is scheduled to be commissioned: use the hostname from the procurement ticket as Name and PLANNED as State

- If host is a pure spare host, not to be commissioned: Use the asset tag as Name and INVENTORY as State

- Hardware warranties should be listed on the order ticket, most servers are three years after ship date.

- Network equipment has one year coverage, which we renew each year as needed for various hardware.

- A Phabricator task should exist with racking location and other details; made during the post-order steps above.

### Requested -> Planned additional steps & Spare -> Planned

- A hostname must be defined at this stage:

- Please see Server naming conventions for details on how hostnames are determined.

- If hostname was not previously assigned, a label with name must be affixed to front and back of server.

- If system has a front LCD, please see instructions on how to set the name on it via Platform-specific documentation

- Run the Netbox ProvisionServerNetwork Script to assign mgmt IP, primary IPv4/IPv6, vlan and switch interface

- Follow the DNS/Netbox#Update_generated_records to create and deploy the mgmt and primary IPs (for mgmt should include both the $assettag.mgmt.site.wmnet as well as $hostname.mgmt.site.wmnet).

- Run the sre.network.configure-switch-interfaces cookbook to configure the switch side.

- If any issue with the above, please report it to Netops and use Homer  instead.

- System Bios & out of band mgmt settings are configured at this time.

- See the Platform-specific documentation for setup instructions for each system type looking for the Initial System Setup section.

- NB: for Dell servers the process is automated, see SRE/Dc-operations/Platform-specific_documentation/Dell_Documentation#Automatic_setup.

- Serial Redirection and mgmt must be tested at this time

- On-site Tech should fully test the mgmt interface to ensure it responds to ssh, they are able to login, reboot the system, and watch a successful BIOS POST over serial console.

### Planned -> Active

#### Preparation

- Decide on partition mapping & add server to modules/profile/data/profile/installserver/preseed.yaml

- Detailed implementation details for our Partman install exist.

- The majority of systems should use automatic partitioning, which is set by inclusion on the proper line in netboot.cfg.

- Any hardware raid would need to be setup manually via rebooting and entering raid bios.

- Right now there is a mix of hardware and software raid availability.

- File located @ puppet modules/install_server.

- partman recipe used located in modules/install_server

- Please note if you are uncertain on what to pick, you should lean towards LVM.

- Many reasons for this, including ease of expansion in event of filling the disk.

- Check site.pp to ensure that the host will be reimaged into the insetup or insetup_noferm roles based on the requirements. If in doubt check with the service owner.

#### Installation

For virtual machines, where there is no physical BIOS to change, but there is virtual hardware to setup, check Ganeti#Create_a_VM instead.

At this point the host can be installed. From now on the service owner should be able to take over and install the host automatically, asking DC Ops to have a look only if there are issues. As a rule of thumb if the host is part of a larger cluster/batch order, it should install without issues and the service owner should try this path first. If instead the host is the first of a batch of new hardware, then is probably better to ask DC Ops to install the first one. Consider it a new hardware if it differs from the existing hosts by Generation, management card, RAID controller, network cards, BIOS, etc.

Automatic Installation

See the Server_Lifecycle/Reimage section on how to use the reimage script to install a new server. Don' t forget to set the --new CLI parameter.

When a server is placed into service, documentation of the service (not specifically the server) needs to reflect the new server's state. This includes puppet file references, as well as Wikitech documentation pages.

- Example: Some servers have SSH fingerprints listed.

The service owner puts the host in production.

Manual installation

Whenever possible follow the Server_Lifecycle#Automatic_Installation steps.

Warning: if you are rebuilding a pre-existing server (rather than a brand new name), on puppetmaster clear out the old certificate before beginning this process:

 puppetmaster$ sudo puppet cert destroy $server_fqdn

1. Reboot system and boot from network / PXE boot

2. Acquires hostname in DNS

3. Acquires DHCP/autoinstall entries

4. OS installation

Run Puppet for the first time

1. From the cumin hosts (cumin1003.eqiad.wmnet, cumin2002.codfw.wmnet) connect to newserver with install-console.

cumin1001:~$  sudo install-console $newserver_fqdn

It is possible that ssh warns you of a bad key if an existing ssh fingerprint still exists on the cumin host, like:

    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
	Someone could be eavesdropping on you right now (man-in-the-middle attack)!
	It is also possible that a host key has just been changed.
	The fingerprint for the ECDSA key sent by the remote host is
	SHA256:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.
	Please contact your system administrator.
	Add correct host key in /dev/null to get rid of this message.

You can safely proceed with the installation; the next time puppet runs automatically on the puppetmaster this file will be updated.

Try then to do a mock puppet run (it will fail due to lack of certificate signage):

newserver# puppet agent --test
Exiting; no certificate found and waitforcert is disabled

2. On puppetmaster  list all pending certificate signings and sign this server's key

puppetmaster$ sudo puppet cert -l
puppetmaster$ sudo puppet cert -s $newserver_fqdn

3. Back to the newserver, enable puppet and test it

 newserver# puppet agent --enable
 newserver# puppet agent --test

4. After a couple of successful puppet runs, you should reboot newserver just to make sure it comes up clean.
5. The newserver should now appear in puppet and in Icinga.
6. If that is a new server, change the state in Netbox to ACTIVE

7. Run the Netbox script to update the device with its interfaces and related IP addresses (remember to Commit the change, the default run is just a preview).

Note: If you already began reinstalling the server before destroying its cert on the puppetmaster, you should clean out ON THE newserver (with care):

newserver# find /var/lib/puppet/ssl -type f -exec rm {} \;

### Spare -> Failed & Planned -> Failed

If a device in the Spare or Planned state has hardware failures it can be marked in Netbox as FAILED.

### Spare -> Decommissioned

When a host in the spare pool has reached its end of life and must be unracked.

- DC Ops perform actions to safely unrack the host, see the #Reclaim to Spares OR Decommission section below.

### Active -> Failed

When a host fails and requires physical maintenance/debugging by DC Ops:

- Service owner perform actions to remove it from production, see the #Remove from production section below.

- Service owner changes Netbox's state to FAILED

- Once the failure is resolved the host will be put back into ACTIVE.

### Active -> Decommissioned

When the host has completed its life in a given role and should decommissioned or returned to the spare pool for re-assignement.

- Service owner perform actions to remove it from production, see the #Remove from production section below.

- Follow instructions for Server Lifecycle#Reclaim to Spares OR Decommission

### Failed -> Spare

When the failure of a Spare device has been fixed it can be set back to INVENTORY in Netbox.

### Failed -> Planned

When the failure of a Planned device has been fixed it can be set back to PLANNED in Netbox.

### Failed -> Active

When the failure of an Active device has been fixed, it can be set back to  ACTIVE in Netbox.

If it has stayed in FAILED long enough to drop out of puppet and DNS, you will need to run sre.puppet.sync-netbox-hiera and sre.dns.netbox

### Failed -> Decommissioned

When the failure cannot be fixed and the host is not anymore usable it must be decommissioned before unracking it.

- Follow instructions for Server Lifecycle#Reclaim to Spares OR Decommission.

### Decommissioned -> Spare

When a decommissioned host is going to be part of the spare pool.

- DC Ops wipe and power down the host, see the #Reclaim to Spares OR Decommission section below.

- DC Ops changes Netbox's state to INVENTORY

### Decommissioned -> Active

When a host is decommissioned from one role and immediately returned in service in a different role, usually with a different hostname.

- Follow Server Lifecycle#Rename while reimaging

### Decommissioned -> Unracked

The host has completed its life and is being unracked

- DC Ops perform actions to safely unrack the host, see the #Reclaim to Spares OR Decommission section below.

### Unracked -> Recycled

When the host physically leaves the datacenter.

- DC Ops perform actions to recycle the host, see the #Reclaim to Spares OR Decommission section below.

If Juniper device, fill the "Juniper Networks Service Waiver Policy" and send it to Juniper through a service request so it's removed from Juniper's DB.

## Server actions

### Reimage

See the Server Lifecycle/Reimage page.

### Remove from production

Please use the Phabricator form for decommission tasks: https://phabricator.wikimedia.org/project/profile/3364/

- A Phabricator ticket should be created detailing the reinstallation in progress.

- System services must be confirmed to be offline.  Make sure no other services depend on this server.

- Remove from pybal/LVS (if applicable) - see the sre.hosts.reimage cookbook option -c/--conftool and consult the LVS  page

- Check if server is part of a service group. For example db class machines are in associated db-X.php, memcached in mc.php.

- Remove server entry from DSH node groups (if applicable). For example check operations/puppet:hieradata/common/scap/dsh.yaml

### Rename while reimaging

- Make sure the host is depooled

- Add the new name to Puppet (at least site.pp, preseed.yaml)

- Run puppet on the install servers: cumin 'A:installserver-full' 'run-puppet-agent -q'

- Run the sre.hosts.rename cookbook

- For example sre.hosts.rename -t T00000 oldname0000 newname0000

- Run the Server Lifecycle/Reimage cookbook with at least the --new option

- In codfw row A and B, add the --move-vlan option to migrate the host the per rack vlan setup

- If the host has the BGP flag set to true in Netbox, run Homer on the local core routers (eg. cr*-codfw*) and its top-of-rack switch (eg. lsw1-b5-codfw*)

- Notify DCops to update the physical label on the hosts

Notes

- The rename cookbook doesn't work in --dry-run until at least https://phabricator.wikimedia.org/T365680 is resolved

- This is for physical hosts only

- The host will need to be re-imaged, and thus lost all its data

- This is only to change a host's name, not change its vlan or realm

- If an iDRAC upgrade is required, either try SRE/Dc-operations/Platform-specific documentation/Dell Documentation#Updating Firmware or ask DCops

#### Old procedure (and for changing vlan if you really need it)

Assumptions:

- The host will lose all its data.

- The host can change primary IPs. The following procedure doesn't guarantee that they will stay the same.

- If the host need to be also physically relocated, follow the additional steps inline.

- A change of the host's VLAN during the procedure is supported.

Procedure:

This procedure follows the active -> decommissioned -> active path. All data on the host will be lost.

- Remove the host from active production (depool, failover, etc.)

- Run the  sre.hosts.decommission cookbook with the --keep-mgmt-dns flag, see Spicerack/Cookbooks#Run_a_single_Cookbook

- If the host needs to be physically relocated:

- Physically relocate the host now.

- Update its device page on Netbox to reflect the new location.

- Get the physical re-labeling done (open a task for dc-ops)

- Update Netbox and edit the device page to set the new name (use the hostname, not the FQDN) and set its status from DECOMMISSIONING to PLANNED.

- Take note of the primary interface connection details: Cable ID, Switch name, Switch port, interface speed (see image on the right). They will be needed in a following step.

- [TODO: automate this step into the Netbox provisioning script] Go to the interfaces tab in the device's page on Netbox, select all the interfaces except the mgmt one, proceed only if the selected interfaces have no IPs assigned to them. Delete the selected interfaces.

- Run the ProvisionServer Netbox script, filling the previously gathered data for switch, switch interface and cable ID (just the integer part). Note: the "Switch port" field needs the last digit of the "full port name". Eg. for "ge-3/0/3" insert just "3". Fill out all the remaining data accordingly, ask for help if in doubt.

- Run the sre.dns.netbox cookbook: DNS/Netbox#Update_generated_records

- Run the sre.network.configure-switch-interfaces cookbook in order to configure the switch interface

- Patch puppet:

- Adjust install/roles for the new server, hieradata, conftool, etc.

- Update partman entry.

- Get it reviewed, merge and deploy it.

- Run puppet on the install servers: cumin 'A:installserver-full' 'run-puppet-agent -q'

- Run the provision cookbook: cookbook sre.hosts.provision --no-dhcp --no-users $hostname

- Follow the reimage procedure at Server Lifecycle/Reimage using the --new option

### Reclaim to Spares OR Decommission

TODO: this section should be split in three: Wipe, Unrack and Recycle.

#### Steps for non-LVS hosts

- Run decomm cookbook, Note: this will also schedule downtime for the host

 $ cookbook sre.hosts.decommission  mc102[3-4].eqiad.wmnet -t T289657

- Remove any references in puppet, most notably from site.pp.

#### Steps for ANY Opsen

- A Decommission ticket should be created detailing if system is being decommissioned (and removed from datacenter) or reclaimed (wiped of all services/data and set system as spare for reallocation).

- Please put a full decommission checklist of the steps in the main task description, this ensures none are accidentally missed.

- System services must be confirmed to be offline.  Checking everything needed for this step and documenting it on this specific page is not feasible at this time(but we are working to add them all).  Please ensure you understand the full service details and what software configuration files must be modified.  This document will only list the generic steps required for the majority of servers.

- If server is part of a service pool, ensure it is set to false or removed completely from pybal/LVS.

- Instructions on how to do so are listed on the LVS page.

- If possible, use tcpdump to verify that no production traffic is hitting the services/ports

- If server is part of a service group, there will be associated files for removal or update.  The service in question needs to be understood by tech performing the decommission (to the point they know when they can take things offline.)  If assistance is needed, please seek out another operations team member to assist.

- Example: db class machines are in associated db-X.php, memcached in mc.php.

- Remove server entry from DSH node groups (if any).

- If the server is part of a service group, common DSH entries are populated from conftool, unless they're proxies or canaries

- The list of dsh groups is in operations/puppet:hieradata/common/scap/dsh.yaml.

- Run the  sre.hosts.decommission decom script available on the cluster::management hosts (cumin1003.eqiad.wmnet, cumin2002.codfw.wmnet). The cookbooks is destructive and would make the host unbootable. This script works for both physical hosts and virtual machines. The script will check for remaining occurrences of the hostname or IP in any puppet or DNS files and warn about them. Since at this point the workflow is that you should only remove the host from site.pp and DHCP after running it it is normal that you see warnings about those. You should check though if it still appears in any other files where it is not expected. Most notable case would be that an mw appserver happens to be an mcrouter proxy which needs to be replaced before decom. The actions performed by the cookbook are:

- Downtime the host on Icinga (it will be removed at the next Puppet run on the Icinga host)

- Detect if Physical or Virtual host based on Netbox data.

- If virtual host (Ganeti VM)

- Ganeti shutdown (tries OS shutdown first, pulls the plug after 2 minutes)

- Force Ganeti->Netbox sync of VMs to update its state and avoid Netbox Report errors

- If physical host

- Downtime the management host on Icinga (it will be removed at the next Puppet run on the Icinga host)

- Wipe bootloaders to prevent it from booting again

- Pull the plug (IPMI power off without shutdown)

- Every once in a while the remote IPMI command fails. If you get an error that says "Failed to power off", the host can end up in a state where it is wiped from DNS but still in puppetdb which means it will still be in Icinga but alert and the mgmt DNS won't be reachable. The script will tell you which host is the culprit. To recover:

- First try restarting the decom cookbook, since it's idempotent. If it works on a retry, you can continue normally.

- If that doesn't work, power off the host via IPMI manually (using the troubleshooting steps), or ask DC Ops to power the machine off. You should also remove the host from Puppet and from alerting: manually run puppet node deactivate $FQDN on the puppetmaster followed by running puppet agent on the Icinga server. See T277780#6968901.

- Update Netbox state to Decommissioning and delete all device interfaces and related IPs but the mgmt one

- Disable switch interface and remove vlan config in Netbox

- Remove it from DebMonitor

- Remove it from Puppet master and PuppetDB

- If virtual host (Ganeti VM), issue a VM removal that will destroy the VM. Can take few minutes.

- Run the sre.dns.netbox cookbook to propagate the DNS changes or prompt the user for a manual patch if needed in order to remove DNS entries for the production network, hostname management entries and asset tag mgmt entries at this stage.

- Remove switch vlan config and disable switch interface

- Update the related Phabricator task

- Remove all references from Puppet repository:

- site.pp

- DHCP config from lease file (modules/install_server/files/dhcpd/linux-host-entries.ttyS...  filename changes based on serial console settings)

- Partman recipe in modules/profile/data/profile/installserver/preseed.yaml

- All Hiera references both individual and in regex.yaml

#### Steps for DC-OPS (with network switch access)

- Confirm all puppet manifest entries removal, DSH removal, Hiera data removal.

- Update associated Phabricator ticket, detailing steps taken and resolution.

- If system is decommissioned by on-site tech, they can resolve the ticket.

- If system is reclaimed into spares, ticket should be assigned to the HW Allocation Tech so he can update spares lists for allocation.

#### Decommission Specific (can be done by DC Ops without network switch access)

- A Phabricator ticket for the decommission of the system should be placed in the #decommission project and the appropriate datacenter-specific ops-* project.

- The decom script can be run by anyone in SRE, but then reassign the server to the local DC ops engineer to wipe disks for return to service/spares, or reset bios and setttings and unrack for decommissio

- Run the Offline a device with extra actions Netbox script that will set the device in Offline status and delete all its interfaces and associated IP addresses left.

- To run the script in dry-run mode, uncheck the Commit changes checkbox.

- Remove its mgmt DNS entries: run the sre.dns.netbox cookbook

- Unless another system will be placed in the space vacated immediately, please remove all power & network cables from rack.

#### Network devices specific

- SRX only: ensure autorecovery is disabled (see Juniper doc)

- Wipe the configuration

- By either running the command request system zeroize media

- Or Pressing the reset button for 15s

- Confirm the wipe is successful by login to the device via console (root/no password)

### Move existing server between rows/racks, changing IPs

Experimental procedure, not yet fully tested

Procedure:

This procedure follows the active -> decommissioned -> active path. All data on the host will be lost.

- Remove the host from active production (depool, failover, etc.)

- Run the  sre.hosts.decommission cookbook with the --keep-mgmt-dns, see Spicerack/Cookbooks#Run_a_single_Cookbook

- Physically relocate the host now.

- Update Netbox

- Update Netbox device page with new rack location

- Delete the cables connected to the device's interfaces (write down their ID if going to reuse them)

- Delete *all* Netbox interfaces for the device, except for the 'mgmt' one. DO NOT USE THE "DELETE" BUTTON IN THE UPPER-RIGHT-HAND CORNER, THIS WILL COMPLETELY DELETE THE DEVICE!

- Change Netbox status for the device from 'decommissioned' to 'planned'

- Run the Provision Server Netbox script, providing the new switch and port, along with the cable ID and vlan detail (as normal, ask for help if in doubt).

- Verify that the device now has 2 interfaces in Netbox, mgmt and ## PRIMARY ##, each with an IP assigned

- Run the sre.dns.netbox cookbook: DNS/Netbox#Update_generated_records

- Run the sre.network.configure-switch-interfaces cookbook to configure the switch interface

- If any firmware upgrades are required to reimage the server, apply them now (this is no different than any reimage/upgrade)

- Patch puppet:

- This steps here only adjust Netbox records and those generated from them.

- Any hardcoded references to the old IP addresses in the puppet repo need to be changed also

- This will vary from server to server depending on what it does, what talks to it

- Bear in mind interface names can also change after reimage (if OS or firmware upgraded during process), so references to those may also need updating

- Run puppet on the install servers: cumin 'A:installserver' 'run-puppet-agent -q'

- Run the sre.hosts.reimage cookbook with the --new option, following the procedure at Server Lifecycle/Reimage

- If the server has more than a single network interface:

- The reimage will run the PuppetDB import script to add any additional host interfaces / switch connections in Netbox

- In Netbox set the correct Vlan(s) on the switch ports for the 2nd and subsequent interfaces (if unsure ask netops what is needed)

- Run the the sre.network.configure-switch-interfaces cookbook to configure the additional interfaces on the switch

### Change server NIC and switch connection, keeping IPs

#### Why?

Upgrading NIC speed, see T322082 for an example.

#### Procedure

- If necessary, find new network device name, replace old netdev name in interfaces file: sed -i s/eno1/enp59s0f0np0/g /etc/network/interfaces

- Shut down the server

- Use the Netbox script to move servers within the same row

- Physical move + recable

- Run homer to configure the switch ports, for example:  homer asw2-a-eqiad* commit "a message"

- (Optional) Upgrade idrac and NIC firmware: cookbook sre.hardware.upgrade-firmware -n -c idrac -n nic <fqdn>

- Run provisioning cookbook: cookbook sre.hosts.provision --no-dhcp --no-users $hostname

- Run the .puppet.sync-netbox-hiera cookbook: sre.puppet.sync-netbox-hiera -t ${task} "Update location of $hostname"

- Start the host from the DRAC/iLO racadm serveraction powerup or via IPMI or via Redfish or physically.

- If you missed the network config in step one, correct it now via the DRAC/iLO

- Login to the host

- Check the logs of the Puppet run at boot time (either locally or on Puppetboard)

- Run Puppet again to ensure it's a noop

- Run the import from the PuppetDB Netbox script

- Check that everything looks correct

## Helpful Cheats

### Finding hosts to Decomm

Example: Find servers with purchased before 2018-11-16, status active or failed and name starting with mw:

https://netbox.wikimedia.org/dcim/devices/?role_id=1&status=active&status=failed&name__isw=mw&cf_purchase_date__lt=2018-11-16

Important Parameters (either via UI or URL):

- name__isw: host name prefix

- cf_purchase_date__lt: purchase date (less than)

Exporting Data: Click on "Export" on top right, to export the list as CSV

Retrieved from "https://wikitech.wikimedia.org/w/index.php?title=Server_Lifecycle&oldid=2368403"

Categories:
- Operations
- SRE Infrastructure Foundations
