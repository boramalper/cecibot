# AWS (Amazon Web Services) - Guide & Tips

## Boto 3

### Essential Configuration
1. Save your credentials at `~/.aws/credentials`:

       [default]
       aws_access_key_id=YOUR_ACCESS_KEY
       aws_secret_access_key=YOUR_SECRET_KEY

2. Set the default region at `~/.aws/config`:

       [default]
       region=eu-west-1

## EC2
* [Troubleshooting Connecting to Your Instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/TroubleshootingInstancesConnecting.html)

## Route 53
* [Migrating DNS Service for an Inactive Domain](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/migrate-dns-domain-inactive.html)
