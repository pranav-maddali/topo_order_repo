#!/usr/local/cs/bin/python3

import os
import zlib
import sys
from collections import defaultdict


def topo_order_commits():
    curr_dir = os.getcwd()
    dot_git = find_dot_git(curr_dir)

    branches = get_branches(dot_git)

    commit_nodes, root_hashes = build_commit_graph(dot_git)

    topo_ordered_commits = get_topo_ordered_commits(commit_nodes, root_hashes)

    print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_commits, branches)


def find_dot_git(path):
    while path != "/":
        if ".git" not in os.listdir(path):
            path = os.path.dirname(path)
        else:
            return os.path.join(path, ".git")

    print("Not inside a git repository", file=sys.stderr)
    exit(1)


def get_branches(path):
    branches_info = defaultdict(list)
    branch_names = []
    git_refs = os.path.join(path, "refs/heads")

    sub_dir = ""
    for root, dirs, files in os.walk(git_refs, topdown=True):
        for file in files:
            if root != git_refs:
                sub_dir = root[len(git_refs)+1:]
            if sub_dir == "":
                branch_names.append(file)
            else:
                branch_names.append(sub_dir+"/"+file)

    for name in branch_names:
        f = open(os.path.join(git_refs, name), 'r')
        branch_hash = f.read().strip('\n')
        branches_info[branch_hash].append(name)

    return branches_info


def build_commit_graph(path):
    commits_info = dict()
    commits = []
    root_commits = []
    objects = os.path.join(path, "objects")

    for root, dirs, files in os.walk(objects, topdown=True):
        for file in files:
            temp = root + "/" + file
            compressed_contents = open(temp, 'rb').read()
            decompressed_contents = zlib.decompress(compressed_contents)
            if decompressed_contents.startswith(b'commit'):
                if temp != objects:
                    temp = temp[len(objects)+1:]
                # storing eg: a1/b2c3
                commits.append(temp)

    # changing a1/b2c3 -> a1b2c3
    commit_hashes = [(c[:2]+c[3:]) for c in commits]

    for idx, c in enumerate(commits):
        c_hash = commit_hashes[idx]

        # path = ~/.git/objects/a1/b2c3
        commit_path = objects + "/" + c
        compressed_data = open(commit_path, 'rb').read()
        decompressed_data = zlib.decompress(compressed_data)
        lines = decompressed_data.split(b'\n')

        parent_hashes = set()
        for line in lines:
            if line.startswith(b'parent'):
                parent_hashes.add((line[len("parent")+1:]).decode("utf-8"))

        # add commit to the dictionary
        if c_hash not in commits_info:
            commits_info[c_hash] = CommitNode(c_hash)
        # add parent to dictionary, and necessary updates
        if parent_hashes:
            commits_info[c_hash].parents.update(parent_hashes)
            for p_hash in parent_hashes:
                if p_hash not in commits_info:
                    commits_info[p_hash] = CommitNode(p_hash)
                commits_info[p_hash].children.add(c_hash)

    for commit in commits_info:
        if len(commits_info[commit].parents) == 0:
            root_commits.append(commit)

    return commits_info, root_commits


def get_topo_ordered_commits(commit_nodes, root_hashes):
    visited = set()
    order = []
    stack = sorted(root_hashes)

    while stack:
        v = stack[-1]
        flag = False
        visited.add(v)
        # use a sorted set to ensure the output is deterministic
        for c in sorted(commit_nodes[v].children):
            if c not in visited:
                stack.append(c)
                flag = True
                break
        """added this to mimic recursion for the
        previous for loop and by-pass appending the
        commit to check if it has any children"""
        if flag is False:
            order.append(v)
            stack.pop()

    return order


def print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_commits, head_to_branches):
    jumped = False
    for idx in range(len(topo_ordered_commits)):
        commit_hash = topo_ordered_commits[idx]

        if jumped:
            jumped = False
            sticky_hash = ' '.join(commit_nodes[commit_hash].children)
            print(f'={sticky_hash}')

        branches = []
        if commit_hash in head_to_branches:
            branches = sorted(head_to_branches[commit_hash])

        print(commit_hash + (' ' + ' '.join(branches) if branches else ''))

        if (idx+1) < len(topo_ordered_commits) and topo_ordered_commits[idx+1] not in commit_nodes[commit_hash].parents:
            jumped = True
            sticky_hash = ' '.join(commit_nodes[commit_hash].parents)
            print(f'{sticky_hash}=\n')


class CommitNode:
    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()


if __name__ == '__main__':
    topo_order_commits()
