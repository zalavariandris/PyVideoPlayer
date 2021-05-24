#version 330 core

out vec4 color;
in vec2 vUv;
uniform sampler2D screenTexture;
void main(){
    vec3 col = texture(screenTexture, vUv).rgb;
    color = vec4(col, 1.0);
}