import pytest
from app.execution import code_run

@pytest.mark.docker
@pytest.mark.parametrize('language,code,expected',[
    ('python','def solve(nums): return sum(nums)',6),
    ('javascript','function solve(nums) { return nums.reduce((a,b)=>a+b,0); }',6),
    ('java','class Solution { public static Object solve(int[] nums) { int s=0;for(int n:nums)s+=n;return s; } }',6),
])
def test_real_languages(language,code,expected):
    r=code_run(language,code,[1,2,3]);assert r['status']=='ok' and r['value']==expected,r

@pytest.mark.docker
def test_sandbox_denies_network_and_host_writes():
    code='''def solve(nums):
    import socket
    try:
        socket.create_connection(("1.1.1.1",80),timeout=1)
        return "network allowed"
    except OSError:
        pass
    try:
        open("/work/escape.txt","w").write("bad")
        return "write allowed"
    except OSError:
        return "isolated"
'''
    assert code_run('python',code,[])['value']=='isolated'

@pytest.mark.docker
def test_sandbox_limits_output():
    r=code_run('python','def solve(nums):\n    print("x" * 100000)\n    return 0',[])
    assert r['status']=='output_limit'
