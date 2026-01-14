<!-- 默认显示英文版本，通过语言切换显示不同版本 -->
<div align="center">

# Hi there 👋, I'm CGArtLab

### 🎨 Digital Artist & 3D Visual Designer | 🎮 CG Animation & Game Development

</div>

## 🌟 About Me

I am a passionate digital artist and 3D visual designer based in Kunming, Yunnan, China. My work focuses on creating immersive visual experiences through CG animation and game development. With a strong background in design and technology, I blend creativity with technical expertise to craft engaging content across various platforms.

### 🚀 What I Do

- **CG Animation**: Bringing characters and stories to life through detailed animation and visual storytelling
- **Game Development**: Designing interactive and visually stunning game environments, assets, and characters
- **Digital Art**: Creating captivating digital illustrations and concepts for various media
- **Knowledge Management**: Sharing insights on design, animation, and creative processes while continuously learning

### 🛠️ Tools & Technologies

- **3D Tools**: Cinema4D, ZBrush
- **Game Engines**: Unity
- **Design Tools**: Photoshop, Illustrator, After Effects
- **Programming**: C#, JavaScript
- **Project Management**: Obsidian, Notion

---

<div align="center" style="display: none;" id="zh-cn">

# 你好 👋，我是CG艺术实验室

### 🎨 数字艺术家 & 3D视觉设计师 | 🎮 CG动画与游戏开发

</div>

<div align="center" style="display: none;" id="zh-tw">

# 你好 👋，我是CG藝術實驗室

### 🎨 數位藝術家 & 3D視覺設計師 | 🎮 CG動畫與遊戲開發

</div>

<!-- 简体中文版本 -->
<div style="display: none;" id="zh-cn-content">

## 🌟 关于我

我是一名来自中国云南昆明的热情数字艺术家和3D视觉设计师。我的工作专注于通过CG动画和游戏开发创造沉浸式视觉体验。凭借设计和技术的深厚背景，我将创意与技术专长相结合，为各种平台打造引人入胜的内容。

### 🚀 我的专长

- **CG动画**: 通过细致的动画和视觉叙事，为角色和故事赋予生命
- **游戏开发**: 设计互动性强、视觉震撼的游戏环境、资源和角色
- **数字艺术**: 为各种媒体创作引人入胜的数字插画和概念设计
- **知识管理**: 分享设计、动画和创作过程的见解，持续学习和成长

### 🛠️ 工具与技术

- **3D工具**: Cinema4D, ZBrush
- **游戏引擎**: Unity
- **设计工具**: Photoshop, Illustrator, After Effects
- **编程语言**: C#, JavaScript
- **项目管理**: Obsidian, Notion

</div>

<!-- 繁体中文版本 -->
<div style="display: none;" id="zh-tw-content">

## 🌟 關於我

我是一名來自中國雲南昆明的熱情數位藝術家和3D視覺設計師。我的工作專注於透過CG動畫和遊戲開發創造沉浸式視覺體驗。憑藉設計和技術的深厚背景，我將創意與技術專長相結合，為各種平台打造引人入勝的內容。

### 🚀 我的專長

- **CG動畫**: 透過細緻的動畫和視覺敘事，為角色和故事賦予生命
- **遊戲開發**: 設計互動性強、視覺震撼的遊戲環境、資源和角色
- **數位藝術**: 為各種媒體創作引人入勝的數位插畫和概念設計
- **知識管理**: 分享設計、動畫和創作過程的見解，持續學習和成長

### 🛠️ 工具與技術

- **3D工具**: Cinema4D, ZBrush
- **遊戲引擎**: Unity
- **設計工具**: Photoshop, Illustrator, After Effects
- **程式語言**: C#, JavaScript
- **專案管理**: Obsidian, Notion

</div>

---

<div align="center">

### 🌐 Language / 语言 / 語言

[English](#) | [简体中文](#zh-cn) | [繁體中文](#zh-tw)

### Happy Coding & Rendering

</div>

<script>
// 简单的语言切换功能
function switchLanguage(lang) {
    // 隐藏所有语言内容
    document.querySelectorAll('[id^="zh-"]').forEach(el => {
        el.style.display = 'none';
    });

    // 显示默认英文内容
    document.querySelector('div:not([id])').style.display = 'block';

    // 显示选中的语言内容
    if (lang === 'zh-cn') {
        document.getElementById('zh-cn').style.display = 'block';
        document.getElementById('zh-cn-content').style.display = 'block';
        document.querySelector('div:not([id])').style.display = 'none';
    } else if (lang === 'zh-tw') {
        document.getElementById('zh-tw').style.display = 'block';
        document.getElementById('zh-tw-content').style.display = 'block';
        document.querySelector('div:not([id])').style.display = 'none';
    }
}

// 为语言链接添加点击事件
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const lang = this.getAttribute('href').substring(1);
            switchLanguage(lang);
        });
    });
});
</script>
