#!/usr/bin/python
import os
import re
import json
import time
import sys
from datetime import datetime


class bcolors:
    OKGREEN = '\033[92m'
    OKBLUE = '\033[94m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def runcommand(cmd):
    """
    function to execute shell commands and returns a dic of
    """
    import subprocess

    info = {}
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            universal_newlines=True)
    std_out, std_err = proc.communicate()
    # print(std_out.encode('utf-8').decode('cp1252'))
    info['cmd'] = cmd
    info['rc'] = proc.returncode
    info['stdout'] = std_out.rstrip()
    info['stderr'] = std_err.rstrip()
    ## Python's rstrip() method
    # strips all kinds of trailing whitespace by default, not just one newline
    return info


###################################################################
# Main Variables
###################################################################

packer_file = './packer.json'
packer_var_file = './variables.json'
cloudformation_template = './cloudFormation.yaml'
scalingUP_test = True
scalingUP_test_TMOUT = 240

now = datetime.now()
cloudformation_stack = now.strftime("Eslam-%d-%m-%Y-%H-%M-%S")

###################################################################
# Set AK/SK Environment variables  [ Setting them here for testing ]
###################################################################

#os.environ["AWS_ACCESS_KEY_ID"] = ""
#os.environ["AWS_SECRET_ACCESS_KEY"] = ""
#os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


for env in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", 'AWS_DEFAULT_REGION']:
    if not env in os.environ:
        print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "The following ENV is missing:  >> {} <<".format(env))
        print("\t --> Make sure to set the following Environment variables:")
        print("export AWS_ACCESS_KEY_ID=''\nexport AWS_SECRET_ACCESS_KEY=''\nexport AWS_REGION=''")
        exit(1)


###################################################################
# Check dependencies for aws-cli
###################################################################

check_aws_cli_first = runcommand("aws --version")
if check_aws_cli_first['rc'] != 0:
    check_unzip = runcommand("unzip")
    check_wget = runcommand("wget")
    needed_pkgs = []
    for i in [check_unzip, check_wget]:
        if i['rc'] == 127: # 127 exit_code --> Command not found
            needed_pkgs.append(i['cmd'])
    if len(needed_pkgs) > 0:
        print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "The following packages are needed for installing aws-cli: {}".format(needed_pkgs))
        print("\t  Alternatively; you can install aws-cli manually .")
        exit(1)

###################################################################
# Packer
###################################################################

print("")
print(bcolors.WARNING + "[ INFO ] " + bcolors.ENDC + "STAGE 1  **************** Packer ****************")
print("")

# Create dir for output
now = datetime.now()
output_dir = now.strftime("%d-%m-%Y_%H-%M-%S")

if not os.path.isdir('./output'):
    os.mkdir('./output')
os.mkdir("./output/{}".format(output_dir))

# packer validate
check_packer_syntax = runcommand("./packer validate -var-file={} {}".format(packer_var_file, packer_file))
if check_packer_syntax['rc'] != 0:
    print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "Invalid Packer Syntax \n \t--> {}".format(
        check_packer_syntax['stdout']))
    exit(1)

print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "Building the AMI with Packer, might take some time ...")
run_packer = runcommand("./packer build -var-file={} {}".format(packer_var_file, packer_file))
# run_packer = {'rc': 0, 'stdout': 'testing'} # Testing1
# packer build
packer_out_file = './output/{}/packer_output.txt'.format(output_dir)
packer_out = open(packer_out_file, 'w')
packer_out.write(run_packer['stdout'])
packer_out.close()

if run_packer['rc'] != 0:
    print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "Failed to run 'Packer build ...")
    print("\t --> Full Packer Output: ({})".format(packer_out_file))
    exit(1)
print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + bcolors.OKGREEN + "Packer build done successfully" + bcolors.ENDC)
print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "Packer output saved in: ({})".format(packer_out_file))

# Getting the AMI ID

ami_search = re.findall('ami.*', run_packer['stdout'])  # Saving the AMI_ID to a variable, to pass to next STAGE
if len(ami_search) < 1:
    print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "Failed to get AMI_ID; Exiting")
    exit(1)
ami = ami_search[-1].rstrip()
print(
    bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "AMI Created successfully\n \t --> AMI ID: " + bcolors.OKBLUE + "{}".format(
        ami) + bcolors.ENDC)

###################################################################
# CloudFormation
###################################################################

print("")
print(bcolors.WARNING + "[ INFO ] " + bcolors.ENDC + "STAGE 2  **************** CloudFormation ****************")
print("")
check_aws_cli_first = runcommand("aws --version")
if check_aws_cli_first['rc'] != 0:
    print("[ Required ] Installing aws-cli")
    if not os.path.isfile("/tmp/aws-cli.zip"):
        check_wget = runcommand("wget --version")
        if check_wget['rc'] != 0:
            print("[ Required ] Kindly Install wget and run the script again")
            print("[ INFO ] The created AMI: " + bcolors.WARNING + "{}".format(ami) + bcolors.ENDC)
            exit(1)
        runcommand("wget -O /tmp/aws-cli.zip https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip")
    runcommand("""
    sudo rm -rf /tmp/aws
    unzip /tmp/aws-cli.zip -d /tmp/
    sudo /tmp/aws/install
    sudo rm /tmp/aws /tmp/aws-cli.zip -rf
    """)

double_check_aws_cli = runcommand("aws --version")
if double_check_aws_cli['rc'] != 0:
    print(
        bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "Cloud NOT Install aws-cli -- Please install it manually and run the script again")
    exit(1)

# aws cloudformation deploy --template-file cloudFormation.yaml --stack-name testing-cli
print(
    bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "Building the Infrastructure with CloudFormation, might take some time ...")
run_cloudformation = runcommand("aws cloudformation deploy --template-file {} --stack-name {} \
                                 --parameter-overrides  AmiID={}".format(cloudformation_template, cloudformation_stack,
                                                                         ami))
if run_cloudformation['rc'] != 0:
    print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "Failed to run Cloudformation Template\n \t --> {}".format(
        run_cloudformation['stderr']))
    exit(1)
print(
    bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + bcolors.OKGREEN + "CloudFormation Stack Created Successfully" + bcolors.ENDC)

CF_out_file = './output/{}/cloudFormation_output.txt'.format(output_dir)
CF_out = open(CF_out_file, 'w')
CF_out.write(run_cloudformation['stdout'])
CF_out.close()
print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "CloudFormation output saved in: ({})".format(CF_out_file))

###################################################################
# Getting INFO
###################################################################

# Parsing Stack info
stack_show = runcommand("aws cloudformation describe-stacks --stack-name {}".format(cloudformation_stack))
if stack_show['rc'] != 0:
    print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "Could NOT get Stack Output")
    exit(1)
loaded_json = json.loads(stack_show['stdout'])
outputs = loaded_json['Stacks'][0]['Outputs']

Bastion_PublicIP = None
LB_DNS_Name = None
ASG_Name = None
for i in outputs:
    if i['OutputKey'] == 'PublicIP':
        Bastion_PublicIP = i['OutputValue']

for i in outputs:
    if i['OutputKey'] == 'LBName':
        LB_DNS_Name = i['OutputValue']
for i in outputs:
    if i['OutputKey'] == 'ASGName':
        ASG_Name = i['OutputValue']

print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "Stack Info:")
print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "\t --> Bastion Host PublicIP: " + bcolors.OKBLUE + "{}".format(
    Bastion_PublicIP) + bcolors.ENDC)
print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "\t --> Load balancer Dns name: " + bcolors.OKBLUE + "{}".format(
    LB_DNS_Name) + bcolors.ENDC)

asg_show = runcommand("aws autoscaling describe-auto-scaling-groups \
                      --auto-scaling-group-names {}".format(ASG_Name))
autoscaling_json = json.loads(asg_show['stdout'])
desired_capacity = None
instances = None
MinSize = None
MaxSize = None
instances_no = 0
for i in autoscaling_json['AutoScalingGroups']:
    if i['AutoScalingGroupName'] == ASG_Name:
        desired_capacity = i['DesiredCapacity']
        instances = i['Instances']
        MinSize = i['MinSize']
        MaxSize = i['MaxSize']
        instances_no = len(i['Instances'])

# ****************************************************************************************

# Print rolling back commands

desc_ami = runcommand("aws ec2 describe-images --image-id {}".format(ami))
ami_snapshot_json = json.loads(desc_ami['stdout'])
snap_id = None
for i in ami_snapshot_json['Images']:
    if i['ImageId'] == ami:
        snap_id = i['BlockDeviceMappings'][0]['Ebs']['SnapshotId']

print("")
print("\t\tTo RollBack:")
print(
    bcolors.WARNING + "\t\taws cloudformation delete-stack --stack-name {}".format(cloudformation_stack) + bcolors.ENDC)
print(bcolors.WARNING + "\t\taws ec2 deregister-image --image-id {}".format(ami) + bcolors.ENDC)
print(bcolors.WARNING + "\t\taws ec2 delete-snapshot --snapshot-id {}".format(snap_id) + bcolors.ENDC)

###################################################################
# Testing
###################################################################

if scalingUP_test:
    print("")
    print(bcolors.WARNING + "[ INFO ] " + bcolors.ENDC + "STAGE 3  **************** Testing ****************")
    print("")
    print(
        bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "Watching for the Number of Instances to increase ... [ TMOUT = {}/S ({} Minutes) ]".format(
            scalingUP_test_TMOUT, scalingUP_test_TMOUT//60))
    print("\t\t - Desired_Capacity: {}".format(desired_capacity))
    print("\t\t - Instances Max Size: {}".format(MaxSize))
    print("\t\t - Instances Min Size: {}".format(MinSize))

    time_Elapsed = 0
    time_to_run = 0
    while time_Elapsed < scalingUP_test_TMOUT:
        signal = False
        TMOUT_signal = False
        while not instances_no > desired_capacity:  # Running the following command each 15 second
            time_Elapsed += 1
            if time_Elapsed > time_to_run:
                # EXAMPLE: increment "time_to_run" by 15 -- and when  (instances_no > time_to_run) i.e 16 > 15,
                # re increment "time_to_run" by another 15 and so on.
                # The goal is to execute a command every 15/s in a while loop that sleeps every 1 second ^_^
                time_to_run += 15
                asg_show = runcommand("aws autoscaling describe-auto-scaling-groups \
                                                  --auto-scaling-group-names {}".format(ASG_Name))
                autoscaling_json = json.loads(asg_show['stdout'])
                for i in autoscaling_json['AutoScalingGroups']:
                    if i['AutoScalingGroupName'] == ASG_Name:
                        instances_no = len(i['Instances'])

            sys.stdout.write("\r")
            sys.stdout.write(
                "\t\t - Current Instances Number: {}      (Time Elapsed: {}/S)".format(instances_no, time_Elapsed))
            sys.stdout.flush()
            time.sleep(1)

            if instances_no > desired_capacity:
                signal = True
                break
            elif time_Elapsed == scalingUP_test_TMOUT:
                TMOUT_signal = True
                break
        if signal:
            print("")
            print(bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + "Instances_Number increased to {}".format(
                instances_no))
            print(
                bcolors.OKGREEN + "[ INFO ] " + bcolors.ENDC + bcolors.OKGREEN + "Scaling UP Test is PASS " + bcolors.ENDC)
            print("")
            print(bcolors.OKGREEN + "\t\t   **************** DONE **************** " + bcolors.ENDC)
            break
        if TMOUT_signal:
            print("")
            print(bcolors.FAIL + "[ ERROR ] " + bcolors.ENDC + "TIME OUT o_O")
print("")
