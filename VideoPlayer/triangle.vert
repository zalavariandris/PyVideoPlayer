#version 330 core
out vec2 vUv;

layout (location = 0) in vec3 position;
layout (location = 1) in vec2 uv;
layout (location = 2) in vec3 normal;

void main(){
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
}