#!/bin/bash
# Video Agent 测试套件
# 分阶段运行测试

set -e

echo "=================================================="
echo "🧪 Video Agent 测试套件"
echo "=================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查环境
echo "🔍 检查测试环境..."

if [ ! -f "config/config.yaml" ]; then
    echo -e "${RED}❌ 错误: 配置文件不存在${NC}"
    echo "   请复制 config/config.yaml 并填写配置"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: Python3 未安装${NC}"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  警告: FFmpeg 未安装，某些测试可能失败${NC}"
    echo "   Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "   macOS: brew install ffmpeg"
fi

echo -e "${GREEN}✅ 环境检查通过${NC}"
echo ""

# 运行 Phase 1
run_phase1() {
    echo "=================================================="
    echo "🚀 运行 Phase 1: 抓取能力测试"
    echo "=================================================="
    echo ""
    
    cd tests
    python3 test_phase1.py
    cd ..
    
    echo ""
    read -p "Phase 1 测试完成。是否继续 Phase 2? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "测试结束"
        exit 0
    fi
}

# 运行 Phase 2
run_phase2() {
    echo ""
    echo "=================================================="
    echo "🚀 运行 Phase 2: 处理能力测试"
    echo "=================================================="
    echo ""
    
    cd tests
    python3 test_phase2.py
    cd ..
}

# 运行全部测试
run_all() {
    run_phase1
    run_phase2
    
    echo ""
    echo "=================================================="
    echo "🎉 所有测试完成!"
    echo "=================================================="
}

# 显示帮助
show_help() {
    cat << EOF
Video Agent 测试套件

用法:
  ./run_tests.sh [选项]

选项:
  all      运行全部测试 (Phase 1 + Phase 2)
  phase1   仅运行 Phase 1 (抓取能力测试)
  phase2   仅运行 Phase 2 (处理能力测试)
  help     显示此帮助信息

测试说明:
  Phase 1 - 验证 YouTube 监控和视频下载
            需要: 配置好 YouTube 频道
            输出: downloads/ 目录的视频文件
            
  Phase 2 - 验证视频处理流程
            需要: Phase 1 通过，有本地视频
            输出: outputs/test/ 目录的处理后视频

示例:
  ./run_tests.sh all      # 运行完整测试
  ./run_tests.sh phase1   # 仅测试抓取
  ./run_tests.sh phase2   # 仅测试处理

EOF
}

# 主逻辑
case "${1:-all}" in
    phase1)
        run_phase1
        ;;
    phase2)
        run_phase2
        ;;
    all)
        run_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "未知选项: $1"
        show_help
        exit 1
        ;;
esac
