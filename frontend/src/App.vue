<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="wy-page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>
