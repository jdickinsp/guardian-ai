def clone_github_repo(repo_url):
    # save to tmp directory
    # make tmp directory if it doesn't exist
    """
    When cloning a project, manually or via script, you can add the GitHub username to prevent collisions.
    Store repositories under folders based on GitHub usernames or organizations to avoid name conflicts.
    for example
    mkdir -p ~/projects/github.com/username && cd ~/projects/github.com/username
    git clone https://github.com/username/project_name.git
    """
    pass


def segment_codebase(code):
    """
    use tree sitter to segment code for embeddings
    """
    pass


def create_embeddings(repo_info, segmented_code):
    """
    create embeddings using ollama nomic-embed-text
    """
    pass


def create_vector_indexes(repo_info, segmented_code, embeddings):
    """
    use faiss to create indexes and save to /bin folder.
    save mapping of code to embeddings in the sqlite database
    """
    pass


def search_similar_code(repo_info, new_context):
    """
    create embeddings for the new_context
    use that to search the faiss indexes for the repo and find similar embeddings
    find the mapping between those embeddings and return the information stored in the sqlite database
    """
    pass
