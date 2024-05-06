function get_public_subnets {
    vpc_id=$1
    subnets=""
    describe_subnets=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=tag:Name,Values=*Public*" --query="Subnets[].SubnetId" --output text))
    for subnet in "${describe_subnets[@]}"
    do
        subnets+="$subnet,"
    done
    subnets=${subnets%,}
    retval=$subnets
}

function get_private_subnets {
    vpc_id=$1
    subnets=""
    describe_subnets=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=tag:Name,Values=*Private*" --query="Subnets[].SubnetId" --output text))
    for subnet in "${describe_subnets[@]}"
    do
        subnets+="$subnet,"
    done
    subnets=${subnets%,}
    retval=$subnets
}