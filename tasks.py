import datetime
import sys
import uuid

from invoke import task, tasks

from pybatfish.client.session import Session


@task()
def docker_build(ctx, dockerfile="", tag=None):
    """
    Docker build task.
    """
    if not dockerfile:
        sys.exit("Dockerfile not provided to docker build, exiting")

    if not tag:
        docker_tag = "latest"
    else:
        docker_tag = tag

    command = f"docker build -t batfish/{docker_tag} -f {dockerfile} ."
    ctx.run(command)
    print("\n\n Docker build completed\n\n")

@task(
    optional=["publish_exposed_ports"]  # user can also provide a ports list with this.
)
def docker_run(ctx, image="", name="", publish_exposed_ports=False):
    if not image:
        sys.exit("Docker image not provided to docker run, exiting")

    if not name:
        docker_name="batfish"
    else:
        docker_name=name

    if publish_exposed_ports:
        if isinstance(publish_exposed_ports, list):
            # user has provided a list
            ports = ""
            for port in publish_exposed_ports:
                if not isinstance(port, str):
                    sys.exit(f"Port provided is not of type str: {port}, exiting")
                ports += f" -p {port}:{port}"
            command = f"docker run{ports} --detach --rm --name {docker_name} {image}"
        else:
            command = f"docker run -d -P --rm --name {docker_name} {image}"
    else:
        command = f"docker run -d --rm --name {docker_name} {image}"

    ctx.run(command)

    print("\n\nDocker run done\n\n")

@task()
def docker_stop(ctx, name="batfish"):
    ctx.run(f"docker stop {name}")

@task(
    pre=[
        tasks.call(docker_build, dockerfile="Dockerfile-batfish"),
        tasks.call(docker_run, image="batfish/latest", publish_exposed_ports=["8888", "9996", "9997"]),
    ],
    post=[tasks.call(docker_stop),]
)
def bgp_sessions(ctx, region="", site=""):
    '''
    Analyze BGP sessions for a site using Batfish.
    '''
    if not site or not region:
        sys.exit("Site/region not given -- do not know which site to analyze BGP sessions for, exiting!")

    # ctx.run("mkdir -p /tmp/batfish/snapshots")  # create snapshots directory

    bf = Session(host="localhost", ssl=False, verify_ssl_certs=False)
    bf.set_network(f"{site}")

    SNAPSHOT_DIR = f'./regions/{region}/{site}/'
    tmp_uuid = uuid.uuid1().hex
    bf.init_snapshot(SNAPSHOT_DIR, name=f'snapshot-bgpsessions-{str(datetime.date.today())}-{tmp_uuid}', overwrite=True)

    print("running bgp session status")
    result = bf.q.bgpSessionStatus().answer().frame()
    
    print("BGP sessions analysis:\n")
    for res in result.iloc:
        print(res)
        print("\n")
