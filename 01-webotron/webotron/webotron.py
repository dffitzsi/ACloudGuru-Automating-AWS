import boto3
import click
from botocore.exceptions import ClientError
from pathlib import Path
import mimetypes

session = boto3.Session(profile_name='default')
s3 = session.resource('s3')
@click.group()
def cli():
    "Webotron deploys website to AWS"
    pass

@cli.command('list-buckets')
def list_buckets():
    "List all s3 buckets"
    for bucket in s3.buckets.all():
        print(bucket)

@cli.command('list-bucket-objects')
@click.argument('bucket')
def list_bucket_object(bucket):
    "List Ojects in an S3 bucket"
    for obj in s3.Bucket(bucket).objects.all():
        print(obj)

@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    "Configure Website on S3 Buckets"
    s3_bucket = None

    try:
        s3_bucket = s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={'LocationConstraint': session.region_name}
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            s3_bucket = s3.Bucket(bucket)
        else:
            raise e

    policy = """
    {
    "Version": "2012-10-17",
    "Id": "S3PolicyId1",
    "Statement": [
    {
        "Sid": "IPAllow",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": "arn:aws:s3:::%s/*",
        "Condition": {
            "IpAddress": {"aws:SourceIp": "79.97.148.119/32"},
            "NotIpAddress": {"aws:SourceIp": "54.241.143.188/32"} 
        } 
    } 
    ]
    }
    """ % s3_bucket.name
    policy = policy.strip()

    pol = s3_bucket.Policy()
    pol.put(Policy=policy)

    ws = s3_bucket.Website()
    ws.put(WebsiteConfiguration={
        'ErrorDocument': {
            'Key': 'error.html'
        },
        'IndexDocument': {
            'Suffix': 'index.html'
        }
    })
    return

def upload_file(s3_bucket, path, key):
    content_type = mimetypes.guess_type(key)[0] or 'text/plain'
    s3_bucket.upload_file(
        path,
        key,
        ExtraArgs={
            'ContentType': 'text/html' 
        }) 

@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    "Sync the content of PATHNAME to BUCKET"
    s3_bucket = s3.Bucket(bucket)

    root = Path(pathname).expanduser().resolve()
    
    def handle_directory(target):
        for p in target.iterdir():
            if p.is_dir(): handle_directory(p)
            if p.is_file(): upload_file(s3_bucket, str(p), str(p.relative_to(root)))
            
    handle_directory(root)
    

if __name__ == '__main__':
    cli()
