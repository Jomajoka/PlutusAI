"""
CDK app entry point. Wires together the stacks below.
Run order doesn't matter much at hackathon scale, but keeping resources
split by concern (storage / api / auth / orchestration) makes it easy for
different people to touch different stacks without stepping on each other.
"""

# from stacks.storage_stack import StorageStack
# from stacks.api_stack import ApiStack
# from stacks.auth_stack import AuthStack
# from stacks.orchestration_stack import OrchestrationStack

def main():
    raise NotImplementedError

if __name__ == "__main__":
    main()
