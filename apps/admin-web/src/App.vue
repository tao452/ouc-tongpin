<template>
  <div id="admin-app">
    <DataBoard />
  </div>
</template>

<script setup>
import DataBoard from './views/DataBoard.vue'
</script>

<style>
#admin-app {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 16px;
  box-sizing: border-box;
}
</style>
