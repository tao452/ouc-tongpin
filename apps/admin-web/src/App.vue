<template>
  <div>
    <el-menu mode="horizontal" router>
      <el-menu-item index="/dashboard">📊 数据看板</el-menu-item>
      <el-menu-item index="/review">🛡️ 审核台</el-menu-item>
      <el-menu-item index="/heatmap">🔥 热力图</el-menu-item>
      <el-menu-item index="/login">🔐 登录页</el-menu-item>
    </el-menu>
    <router-view></router-view>
  </div>
</template>
