export BNAME=sache
aws s3 rm --recursive s3://$BNAME && aws s3 rb s3://$BNAME
export BNAME=sae-activations
aws s3 rm --recursive s3://$BNAME && aws s3 rb s3://$BNAME
export BNAME=sae-classification
aws s3 rm --recursive s3://$BNAME && aws s3 rb s3://$BNAME
export BNAME=spotify-album-popularity
aws s3 rm --recursive s3://$BNAME && aws s3 rb s3://$BNAME
export BNAME=weatherbucket-au
aws s3 rm --recursive s3://$BNAME && aws s3 rb s3://$BNAME