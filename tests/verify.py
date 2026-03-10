#!/usr/bin/env python3
"""
测试结果验证工具
快速检查 Phase 1 和 Phase 2 的测试结果
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def check_phase1():
    """验证 Phase 1 结果"""
    print("\n" + "="*60)
    print("🔍 Phase 1 验证: 抓取能力")
    print("="*60)
    
    checks = []
    
    # 1. 检查数据库
    db_path = Path("database/video_agent.db")
    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print(f"✅ 数据库存在: {size:.1f} KB")
        checks.append(("数据库", True, f"{size:.1f} KB"))
        
        # 查询视频数量
        try:
            from database.models import get_session, Video
            session = get_session()
            count = session.query(Video).count()
            pending = session.query(Video).filter(Video.status == 'pending').count()
            downloaded = session.query(Video).filter(Video.status == 'downloaded').count()
            session.close()
            
            print(f"   总视频数: {count}")
            print(f"   待处理: {pending}")
            print(f"   已下载: {downloaded}")
            checks.append(("视频记录", True, f"共{count}条"))
        except Exception as e:
            print(f"⚠️  无法读取数据库: {e}")
            checks.append(("视频记录", False, str(e)))
    else:
        print(f"❌ 数据库不存在")
        checks.append(("数据库", False, "文件不存在"))
    
    # 2. 检查下载目录
    downloads_dir = Path("downloads")
    if downloads_dir.exists():
        videos = list(downloads_dir.glob("*.mp4"))
        total_size = sum(f.stat().st_size for f in videos) / (1024*1024)
        
        if videos:
            print(f"\n✅ 下载目录: {len(videos)} 个视频, {total_size:.1f} MB")
            checks.append(("下载文件", True, f"{len(videos)}个文件"))
            
            # 显示最新的3个
            videos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            print(f"\n   最新下载:")
            for v in videos[:3]:
                mtime = datetime.fromtimestamp(v.stat().st_mtime).strftime("%m-%d %H:%M")
                size = v.stat().st_size / (1024*1024)
                print(f"   • {v.name[:40]}... ({size:.1f}MB, {mtime})")
        else:
            print(f"\n⚠️  下载目录为空")
            checks.append(("下载文件", False, "目录为空"))
    else:
        print(f"\n❌ 下载目录不存在")
        checks.append(("下载文件", False, "目录不存在"))
    
    return checks


def check_phase2():
    """验证 Phase 2 结果"""
    print("\n" + "="*60)
    print("🔍 Phase 2 验证: 处理能力")
    print("="*60)
    
    checks = []
    
    # 1. 检查输出目录
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        # 查找最终视频
        final_videos = list(outputs_dir.rglob("*_final.mp4"))
        
        if final_videos:
            total_size = sum(f.stat().st_size for f in final_videos) / (1024*1024)
            print(f"✅ 找到 {len(final_videos)} 个成品视频")
            print(f"   总大小: {total_size:.1f} MB")
            checks.append(("成品视频", True, f"{len(final_videos)}个"))
            
            # 显示视频信息
            for v in final_videos[:3]:
                size = v.stat().st_size / (1024*1024)
                print(f"   • {v.name}")
                print(f"     路径: {v}")
                print(f"     大小: {size:.1f} MB")
        else:
            print(f"⚠️  未找到成品视频 (*_final.mp4)")
            checks.append(("成品视频", False, "未找到"))
        
        # 检查测试输出
        test_dir = outputs_dir / "test"
        if test_dir.exists():
            test_files = list(test_dir.iterdir())
            print(f"\n✅ 测试目录存在: {len(test_files)} 个文件")
            for f in test_files:
                size = f.stat().st_size / 1024
                print(f"   • {f.name} ({size:.1f} KB)")
        else:
            print(f"\n⚠️  测试目录不存在")
    else:
        print(f"❌ 输出目录不存在")
        checks.append(("成品视频", False, "目录不存在"))
        checks.append(("测试输出", False, "目录不存在"))
    
    # 2. 检查临时文件
    temp_dir = Path("temp")
    if temp_dir.exists():
        temp_files = list(temp_dir.iterdir())
        if temp_files:
            print(f"\n⚠️  临时目录有 {len(temp_files)} 个文件未清理")
        else:
            print(f"\n✅ 临时目录已清理")
    else:
        print(f"\n✅ 无临时文件")
    
    return checks


def generate_report(phase1_checks, phase2_checks):
    """生成测试报告"""
    print("\n" + "="*60)
    print("📊 测试验证报告")
    print("="*60)
    
    print("\n【Phase 1: 抓取能力】")
    for name, passed, info in phase1_checks:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}: {info}")
    
    print("\n【Phase 2: 处理能力】")
    for name, passed, info in phase2_checks:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}: {info}")
    
    # 统计
    all_checks = phase1_checks + phase2_checks
    passed = sum(1 for _, p, _ in all_checks if p)
    total = len(all_checks)
    
    print(f"\n{'='*60}")
    print(f"总计: {passed}/{total} 项通过 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有验证通过! 系统运行正常")
        return 0
    elif passed >= total * 0.7:
        print("\n⚠️  部分验证未通过，建议检查")
        return 1
    else:
        print("\n❌ 大量验证失败，请运行测试脚本")
        return 2


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 Video Agent 测试验证工具")
    print("="*60)
    print("\n快速验证 Phase 1 和 Phase 2 的测试结果")
    
    phase1_checks = check_phase1()
    phase2_checks = check_phase2()
    
    exit_code = generate_report(phase1_checks, phase2_checks)
    
    print("\n💡 提示:")
    print("   如需完整测试，运行: ./tests/run_tests.sh all")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
