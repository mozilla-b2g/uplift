import unittest
import tempfile
import os
import subprocess
import shutil

import gaia_uplift.git as subject

class GitTestBase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix='.scratch_', dir='.')

    def tearDown(self):
        # TODO: Is it possible to only delete directory on a failed test?
        shutil.rmtree(self.scratch)


class RunCmd(GitTestBase):

    def test_defaults(self):
        output = subject.run_cmd(['bash', '-c', 'echo -n hi ; echo -n bye 1>&2'], self.scratch)
        self.assertEqual('hi', output.strip())

    def test_read_out_false(self):
        output = subject.run_cmd(
            ['bash', '-c', 'echo -n hi 1>&2'],
            self.scratch,
            read_out=False
        )
        self.assertEqual(0, output)

    def test_non_zero_exit(self):
        with self.assertRaises(subprocess.CalledProcessError):
            subject.run_cmd(['bash', '-c', 'exit 1'], self.scratch)

    def test_env(self):
        output = subject.run_cmd(['bash', '-c', 'echo $PWD'], self.scratch)
        self.assertEqual(os.path.abspath(self.scratch), output.strip())

    def test_add_to_env(self):
        output = subject.run_cmd(
            ['bash', '-c', 'echo $JOHN'],
            self.scratch,
            env={'JOHN': 'ISCOOL'}
        )
        self.assertEqual('ISCOOL', output.strip())

    def test_delete_from_env(self):
        output = subject.run_cmd(
            ['bash', '-c', 'echo ${HOME}NOTHOME'],
            self.scratch,
            delete_env=['HOME']
        )
        self.assertEqual('NOTHOME', output.strip())

    def test_add_then_delete_env(self):
        output = subject.run_cmd(
            ['bash', '-c', 'echo ${JOHN}ISLAME'],
            self.scratch,
            env={'JOHN': 'ISCOOL'},
            delete_env=['JOHN']
        )
        self.assertEqual('ISLAME', output.strip())

class TestWithRepository(GitTestBase):
    def create_repo(self, contents):
        self.i = 0
        subject.git_op(['init'], self.scratch)
        return self.create_commits(contents)
        

    def create_commits(self, contents):
        commits = []
        for change in contents:
            commit_time = "%d +0000" % (self.i + 1000000000)
            env = {
                'GIT_AUTHOR_DATE': commit_time,
                'GIT_COMMITTER_DATE': commit_time
            }
            for fn in list(change.keys()):
                filename = os.path.join(self.scratch, fn)
                with open(filename, 'w+') as f:
                    f.write(str(change[fn]))
            subject.git_op(['add'] + list(change.keys()), self.scratch)
            subject.git_op(
                ['commit', '-m', 'commit-%d' % self.i] + list(change.keys()),
                self.scratch, env=env)
            subject.git_op(['tag', str(self.i)], self.scratch)
            commits.append(subject.git_op(['rev-parse', 'HEAD'], self.scratch).strip())
            self.i += 1
        return commits


class TestWithManyRepositories(unittest.TestCase):

    def create_repos(self, count, common_contents):
        self.i = 0
        self.scratch = [tempfile.mkdtemp(prefix='.scratch_', dir='.') for x in range(count)]
        subject.git_op(['init'], self.scratch[0])
        commits = self.create_commits(0, common_contents)
        for x in range(1, count):
            shutil.rmtree(self.scratch[x])
            subject.git_op(['clone', os.path.abspath(self.scratch[0]), self.scratch[x]])
        return commits


    def tearDown(self):
        #[shutil.rmtree(self.scratch[x]) for x in self.scratch]
        pass
        

    def create_commits(self, n, contents):
        commits = []
        for change in contents:
            commit_time = "%d +0000" % (self.i + 1000000000)
            env = {
                'GIT_AUTHOR_DATE': commit_time,
                'GIT_COMMITTER_DATE': commit_time
            }
            for fn in list(change.keys()):
                filename = os.path.join(self.scratch[n], fn)
                with open(filename, 'w+') as f:
                    f.write(str(change[fn]))
            subject.git_op(['add'] + list(change.keys()), self.scratch[n])
            subject.git_op(
                ['commit', '-m', 'commit-%d' % self.i] + list(change.keys()),
                self.scratch[n], env=env)
            subject.git_op(['tag', str(self.i)], self.scratch[n])
            commits.append(subject.git_op(['rev-parse', 'HEAD'], self.scratch[n]).strip())
            self.i += 1
        return commits



class SimpleGitTests(TestWithRepository):
    def test_git_op(self):
        output = subject.git_op(['version'], self.scratch)
        self.assertTrue(output.strip().startswith('git version'))

    def test_create_repo(self):
        result = self.create_repo([{'A': '123', 'B': '345'}, {'A': 'john'}])
        self.assertTrue(len(result) == 2)

    def test_get_rev(self):
        repo_contents = [
            {'A': 1},
            {'A': 2},
            {'A': 3}
        ]
        commits = self.create_repo(repo_contents)

        self.assertEqual(commits[-1], subject.get_rev(self.scratch))
        # Remember, the '2' needs to be a string because the tag is a string
        self.assertEqual(commits[2], subject.get_rev(self.scratch, '2'))

    def test_show(self):
        repo_contents = [
            {'A': 1},
            {'A': 2},
            {'A': 3}
        ]
        commits = self.create_repo(repo_contents)

        self.assertTrue(subject.show(self.scratch).startswith(commits[-1]))
        self.assertTrue(subject.show(self.scratch, '2').startswith(commits[2]))

    def test_valid_id(self):
        ids = ['abcdef1234567',
               'a'*40,
               'f'*40,
               'a'*7,
               'f'*7,
               '1'*40,
               '1'*7]
        for valid_id in ids:
            self.assertTrue(subject.valid_id(valid_id))
    
    def test_invalid_id(self):
        ids = ['a' * 41, 'a' * 6, 'a'*6 + 'g']
        for invalid_id in ids:
            self.assertFalse(subject.valid_id(invalid_id))

    def test__parse_branches(self):
        cmd_out =  "  master\n"
        cmd_out += "  v1.2\n"
        cmd_out += "* v1.3\n"
        self.assertEqual(['master', 'v1.2', 'v1.3'], subject._parse_branches(cmd_out))

    def test_commit_on_branch(self):
        repo_contents = [
            {'A': 1},
            {'A': 2},
            {'A': 3}
        ]
        branch_contents = [
            {'B': 1},
            {'B': 2}
        ]
        commits = self.create_repo(repo_contents)
        subject.git_op(['checkout', '-t', 'master', '-b', 'newbranch'], self.scratch)
        branch_commits = self.create_commits(branch_contents)

        self.assertTrue(subject.commit_on_branch(self.scratch, commits[2], 'master'))
        self.assertTrue(subject.commit_on_branch(self.scratch, commits[2], 'newbranch'))
        self.assertFalse(subject.commit_on_branch(self.scratch, branch_commits[1], 'master'))
        self.assertTrue(subject.commit_on_branch(self.scratch, branch_commits[1], 'newbranch'))

    def test_git_object_type(self):
        commit = self.create_repo([{'A': '1'}])[0] 
        self.assertEqual('commit', subject.git_object_type(self.scratch, commit))

    def test_determine_cherry_pick_master_number(self):
        repo_contents = [
            {'A': 1},
            {'A': 2},
            {'A': 3}
        ]
        branch_contents = [
            {'A': 1},
            {'A': 2}
        ]
        commits = self.create_repo(repo_contents)
        subject.git_op(['checkout', '-t', 'master', '-b', 'newbranch'], self.scratch)
        branch_commits = self.create_commits(branch_contents)
        subject.git_op(['checkout', 'master'], self.scratch)
        subject.git_op(['merge', 'newbranch', '--no-ff'], self.scratch)
        merge_commit = subject.get_rev(self.scratch)
        #raise Exception((merge_commit, self.scratch))
        self.assertEqual(
            '-m1', 
            subject.determine_cherry_pick_master_number(
                self.scratch, 
                merge_commit, 
                'master'
            )
        )
        self.assertEqual(
            None,
            subject.determine_cherry_pick_master_number(
                self.scratch,
                commits[2],
                'master'
            )
        )

    def test_current_branch(self):
        contents = [{'A': '1'}]
        commits = self.create_repo(contents)
        self.assertEqual('master', subject.current_branch(self.scratch))
        subject.git_op(['checkout', '-b', 'newbranch'], self.scratch)
        branch_contents = [{'B': '1'}]
        branch_commits = self.create_commits(branch_contents)
        self.assertEqual('newbranch', subject.current_branch(self.scratch))

    def test_checkout(self):
        contents = [{'A': '1'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, 'master')
        self.assertEqual('master', subject.current_branch(self.scratch))
        subject.checkout(self.scratch, branch_name='newbranch2')
        self.assertEqual('newbranch2', subject.current_branch(self.scratch))
        subject.checkout(self.scratch, 'master')
        self.assertEqual('master', subject.current_branch(self.scratch))
        # There should be a check to see if the newbranch2 is actually tracking
        # master

    def test_merge_ff(self):
        contents = [{'A': '1'}]
        branch_contents = [{'A': '2'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, branch_name='newbranch')
        branch_commits = self.create_commits(branch_contents)
        subject.checkout(self.scratch, 'master')
        
        subject.merge(self.scratch, 'newbranch', ff_only=True)
        self.assertEqual(branch_commits[0], subject.get_rev(self.scratch, id='master'))
        self.assertEqual(1, len(subject.find_parents(self.scratch, 'master')))

    def test_merge_non_ff(self):
        contents = [{'A': '1'}]
        branch_contents = [{'A': '2'}]
        new_master_contents = [{'A': '4'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, branch_name='newbranch')
        branch_commits = self.create_commits(branch_contents)
        subject.checkout(self.scratch, 'master')
        new_master_commits = self.create_commits(new_master_contents)
        
        with self.assertRaises(subject.GitError):
            subject.merge(self.scratch, 'newbranch', ff_only=True)
            #subject.reset(self.scratch)
        subject.merge(self.scratch, 'newbranch', ff_only=False, strategy='ours')
        self.assertEqual(2, len(subject.find_parents(self.scratch, 'master')))

    def test_cherry_pick_noop(self):
        contents = [{'A': '1'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, tracking='master', branch_name='other')
        with self.assertRaises(subject.GitNoop):
            result = subject.cherry_pick(self.scratch, commits[0], 'other', 'master') 

    def test_cherry_pick_commit_not_on_upstream(self):
        contents = [{'A': '1', 'B': '2'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, branch_name='branch')
        branch_contents = [{'C': '3'}]
        branch_commits = self.create_commits(branch_contents)
        subject.checkout(self.scratch, branch_name='other_branch')
        with self.assertRaises(subject.GitError):
            subject.cherry_pick(self.scratch, branch_commits[0], 'other_branch', 'master')

    def test_cherry_pick_commit_not_merge_commit(self):
        contents = [{'A': '1', 'B': '2'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, branch_name='newbranch', tracking='master')
        subject.checkout(self.scratch, 'master')
        new_master_contents = [{'A': '3'}]
        new_master_commits = self.create_commits(new_master_contents)
        branch_commit = subject.cherry_pick(self.scratch, new_master_commits[0], 'newbranch')
        self.assertTrue(subject.commit_on_branch(self.scratch, branch_commit, 'newbranch'))
        self.assertFalse(subject.commit_on_branch(self.scratch, branch_commit, 'master'))

    def test_cherry_pick_commit_is_merge_commit(self):
        contents = [{'A': '1', 'B': '2'}]
        commits = self.create_repo(contents)
        subject.checkout(self.scratch, branch_name='newbranch', tracking='master')
        subject.checkout(self.scratch, branch_name='pr_branch', tracking='master')
        pr_contents = [{'C': '3'}]
        pr_commits = self.create_commits(pr_contents)
        subject.checkout(self.scratch, 'master')
        subject.merge(self.scratch, 'pr_branch', no_ff=True)
        merge_commit = subject.get_rev(self.scratch)
        self.assertEqual(sorted([pr_commits[0], commits[-1]]), sorted(subject.find_parents(self.scratch, merge_commit)))
        branch_commit = subject.cherry_pick(self.scratch, merge_commit, 'newbranch')
        self.assertTrue(subject.commit_on_branch(self.scratch, branch_commit, 'newbranch'))
        self.assertFalse(subject.commit_on_branch(self.scratch, branch_commit, 'master'))

    def test_a_before_b(self):
        contents = [{'A': '1'}, {'A': '2'}, {'A': '3'}]
        commits = self.create_repo(contents)
        cache = {}
        self.assertTrue(
            subject.a_before_b(self.scratch, 'master', {}, commits[0], commits[1])
        )
        self.assertTrue(
            subject.a_before_b(self.scratch, 'master', cache, commits[0], commits[1])
        )
        self.assertFalse(
            subject.a_before_b(self.scratch, 'master', {}, commits[1], commits[0])
        )
        self.assertFalse(
            subject.a_before_b(self.scratch, 'master', cache, commits[1], commits[0])
        )
        self.assertTrue(
            subject.a_before_b(self.scratch, 'master', {}, commits[0], commits[2])
        )
        self.assertTrue(
            subject.a_before_b(self.scratch, 'master', cache, commits[0], commits[2])
        )
        self.assertFalse(
            subject.a_before_b(self.scratch, 'master', {}, commits[2], commits[0])
        )
        self.assertFalse(
            subject.a_before_b(self.scratch, 'master', cache, commits[2], commits[0])
        )        

    def test_sort_commits(self):
        contents = [{'A': x} for x in range(0,10)]
        commits = self.create_repo(contents)
        # Let's shuffle the commits by sorting them alphabetically
        shuffled_commits = sorted(commits)
        self.assertNotEqual(commits, shuffled_commits)
        # Let's also make sure that already sorted input comes out in the
        # same order
        self.assertEqual(commits,
                         subject.sort_commits(self.scratch, commits, 'master'))
        self.assertEqual(commits,
                         subject.sort_commits(self.scratch, shuffled_commits, 'master'))


class GitPushTests(TestWithManyRepositories):
    def test_dry_run_clean(self):
        contents = [{'A': x} for x in range(5)] 
        common_commits = self.create_repos(2, contents)
        new_content = [{'A': x} for x in range(5, 10)]
        new_commits = self.create_commits(1, new_content)
        
        expected = {
            'url': os.path.abspath(self.scratch[0]),
            'branches':{
                'master': (common_commits[-1], new_commits[-1])
            }
        }
        actual = subject.push(self.scratch[1], 'origin', ['master'])
        self.assertEqual(expected['url'], actual['url'])
        self.assertEqual(expected['branches'], actual['branches'])
        self.assertEqual(expected, actual)

        with self.assertRaises(subject.GitError):
            # We chop the commit id down to 7 chars because this
            # forces git to not short-circuit and just echo the
            # full length id it's given.  This also seperates
            # the concern of the git repo having the commit object
            # from a branch having the commit object
            subject.get_rev(self.scratch[0], new_commits[0][:7])

    def test_dry_run_dirty(self):
        contents = [{'A': x} for x in range(5)] 
        common_commits = self.create_repos(2, contents)
        new_content = [{'A': x} for x in range(5, 10)]
        new_commits = self.create_commits(1, new_content)
        new_master_content = [{'A': 10}]
        new_master_commits = self.create_commits(0, new_master_content)

        with self.assertRaises(subject.PushFailure):
            subject.push(self.scratch[1], 'origin', ['master'])


    def test_for_real_clean(self):
        contents = [{'A': x} for x in range(5)] 
        common_commits = self.create_repos(2, contents)
        new_content = [{'A': x} for x in range(5, 10)]
        new_commits = self.create_commits(1, new_content)
        subject.checkout(self.scratch[0], branch_name='notmaster')
        
        expected = {
            'url': os.path.abspath(self.scratch[0]),
            'branches':{
                'master': (common_commits[-1], new_commits[-1])
            }
        }
        actual = subject.push(self.scratch[1], 'origin', ['master'], dry_run=False)

        self.assertEqual(new_commits[0],
            subject.get_rev(self.scratch[0], new_commits[0][:7]))
