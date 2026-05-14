#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROS-connected Pygame 2D room visualizer."""
import json
import math
import threading
from dataclasses import dataclass, field
from typing import Dict, Tuple
import pygame
import rospy
from std_msgs.msg import String

WIDTH, HEIGHT, FPS = 1280, 820, 30
BG=(16,19,24); PANEL=(27,32,40); WALL=(230,235,245); WALL_DARK=(110,120,135)
TEXT=(238,242,248); MUTED=(156,166,180); GREEN=(86,210,135); RED=(235,92,92)
YELLOW=(255,214,88); BLUE=(94,174,255); CYAN=(110,225,240); ORANGE=(255,156,80)
ROOM_OFF=(34,40,50); ROOM_ON=(43,58,50); ROOM_SELECTED=(78,162,255)

@dataclass
class DeviceView:
    key: str; label: str; kind: str; pos: Tuple[int,int]; state: bool=False
    rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0,0,0,0))
@dataclass
class RoomView:
    key: str; label: str; rect: pygame.Rect; devices: Dict[str,DeviceView]; master: bool=False

def draw_text(surface, font, text, color, x, y, center=False):
    img = font.render(str(text), True, color)
    r = img.get_rect()

    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)

    surface.blit(img, r)
    return r

def rounded(surface, color, rect, radius=16, width=0): pygame.draw.rect(surface,color,rect,border_radius=radius,width=width)
def circle_alpha(surface, color, center, radius, alpha):
    o=pygame.Surface((radius*2+4,radius*2+4),pygame.SRCALPHA); pygame.draw.circle(o,(*color,alpha),(radius+2,radius+2),radius); surface.blit(o,(center[0]-radius-2,center[1]-radius-2))
def rect_alpha(surface, color, rect, alpha, radius=12):
    o=pygame.Surface((rect.width,rect.height),pygame.SRCALPHA); pygame.draw.rect(o,(*color,alpha),o.get_rect(),border_radius=radius); surface.blit(o,rect.topleft)

class HomeVisualizerNode(object):
    def __init__(self):
        rospy.init_node('home_visualizer_node', anonymous=False, disable_signals=True)
        self.enable_manual_control=bool(rospy.get_param('~enable_manual_control', True))
        self.lock=threading.Lock(); self.selected_room='room_1'; self.last_action='Waiting for state...'; self.last_source='system'
        self.rooms=self.default_rooms()
        self.command_pub=rospy.Publisher('/home_assistant/command', String, queue_size=10)
        rospy.Subscriber('/home_assistant/state', String, self.state_callback, queue_size=10)
        pygame.init(); pygame.display.set_caption('ROS-style 2D Home Assistant Simulator')
        self.screen=pygame.display.set_mode((WIDTH,HEIGHT)); self.clock=pygame.time.Clock()
        self.font_title=pygame.font.SysFont('arial',32,bold=True); self.font_room=pygame.font.SysFont('arial',24,bold=True)
        self.font=pygame.font.SysFont('arial',21); self.font_small=pygame.font.SysFont('arial',16); self.font_tiny=pygame.font.SysFont('arial',14)
        self.fan_angle=0; self.wind_offset=0; self.curtain_anim=0; self.bubble_phase=0
        self.door_angles={'room_1':0,'room_2':0,'room_3':0}
        self.run()

    def default_rooms(self):
        return {
          'room_1':RoomView('room_1','Room 1 | Bedroom',pygame.Rect(70,110,525,305),{'light':DeviceView('light','Light','light',(165,235)),'fan':DeviceView('fan','Fan','fan',(310,235)),'ac':DeviceView('ac','AC','ac',(465,220)),'door':DeviceView('door','Door','door',(535,345))}),
          'room_2':RoomView('room_2','Room 2 | Living Room',pygame.Rect(610,110,600,305),{'light':DeviceView('light','Light','light',(720,235)),'fan':DeviceView('fan','Fan','fan',(875,235)),'curtain':DeviceView('curtain','Curtain','curtain',(1035,220)),'door':DeviceView('door','Door','door',(1145,345))}),
          'room_3':RoomView('room_3','Room 3 | Toilet',pygame.Rect(70,435,1140,285),{'light':DeviceView('light','Light','light',(190,565)),'exhaust':DeviceView('exhaust','Exhaust Fan','fan',(410,565)),'heater':DeviceView('heater','Water Heater','heater',(680,560)),'door':DeviceView('door','Door','door',(1110,650))})}

    def state_callback(self,msg):
        try: state=json.loads(msg.data)
        except Exception: return
        with self.lock:
            self.selected_room=state.get('selected_room', self.selected_room); self.last_action=state.get('last_action', self.last_action); self.last_source=state.get('last_source','')
            for rk, rd in state.get('rooms',{}).items():
                if rk not in self.rooms: continue
                self.rooms[rk].master=bool(rd.get('master',False))
                for dk,dv in rd.get('devices',{}).items():
                    if dk in self.rooms[rk].devices: self.rooms[rk].devices[dk].state=bool(dv)

    def publish_command(self, room, target, action):
        if self.enable_manual_control:
            self.command_pub.publish(String(data=json.dumps({'source':'gui','room':room,'target':target,'action':action})))

    def run(self):
        while not rospy.is_shutdown():
            dt=self.clock.tick(FPS)/1000.0
            if not self.events(): break
            self.update(dt); self.draw(); pygame.display.flip()
        pygame.quit()

    def events(self):
        for e in pygame.event.get():
            if e.type==pygame.QUIT: rospy.signal_shutdown('window closed'); return False
            if e.type==pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE,pygame.K_q): rospy.signal_shutdown('quit'); return False
                if e.key==pygame.K_1: self.selected_room='room_1'
                elif e.key==pygame.K_2: self.selected_room='room_2'
                elif e.key==pygame.K_3: self.selected_room='room_3'
                elif e.key==pygame.K_o: self.publish_command(self.selected_room,'master_switch','on')
                elif e.key==pygame.K_f: self.publish_command(self.selected_room,'master_switch','off')
                elif e.key==pygame.K_SPACE: self.publish_command(self.selected_room,'master_switch','toggle')
                elif e.key==pygame.K_l: self.publish_command(self.selected_room,'light','toggle')
                elif e.key==pygame.K_v: self.publish_command(self.selected_room,'fan' if 'fan' in self.rooms[self.selected_room].devices else 'exhaust','toggle')
                elif e.key==pygame.K_a: self.publish_command('room_1','ac','toggle')
                elif e.key==pygame.K_c: self.publish_command('room_2','curtain','toggle')
                elif e.key==pygame.K_h: self.publish_command('room_3','heater','toggle')
                elif e.key==pygame.K_d: self.publish_command(self.selected_room,'door','toggle')
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                self.mouse(e.pos)
        return True

    def mouse(self,pos):
        with self.lock:
            for rk,r in self.rooms.items():
                for dk,d in r.devices.items():
                    if d.rect.collidepoint(pos): self.selected_room=rk; self.publish_command(rk,dk,'toggle'); return
            for rk,r in self.rooms.items():
                if r.rect.collidepoint(pos): self.selected_room=rk; return

    def update(self,dt):
        anyfan=any(d.kind=='fan' and d.state for r in self.rooms.values() for d in r.devices.values())
        if anyfan: self.fan_angle=(self.fan_angle+360*dt*1.6)%360
        self.wind_offset=(self.wind_offset+42*dt)%100; self.bubble_phase=(self.bubble_phase+30*dt)%100
        for rk,r in self.rooms.items():
            d=r.devices.get('door'); target=70 if d and d.state else 0; cur=self.door_angles[rk]; speed=180*dt
            self.door_angles[rk]=min(cur+speed,target) if cur<target else max(cur-speed,target)
        c=self.rooms['room_2'].devices['curtain']; target=1 if c.state else 0
        self.curtain_anim=min(self.curtain_anim+dt*3.2,target) if self.curtain_anim<target else max(self.curtain_anim-dt*3.2,target)

    def draw(self):
        self.screen.fill(BG); rounded(self.screen,PANEL,pygame.Rect(40,24,WIDTH-80,64),20)
        draw_text(self.screen,self.font_title,'Local Multi-Modal Home Assistant  |  ROS 2D Room Simulator',TEXT,64,39)
        draw_text(self.screen,self.font,'Manual Control ON' if self.enable_manual_control else 'Display Only',MUTED,WIDTH-280,46)
        for r in self.rooms.values(): self.draw_room(r)
        rounded(self.screen,PANEL,pygame.Rect(40,740,WIDTH-80,58),18)
        draw_text(self.screen,self.font,'Selected: {}'.format(self.rooms[self.selected_room].label.split('|')[0].strip()),BLUE,64,754)
        draw_text(self.screen,self.font,'Last Action: {}'.format(self.last_action),TEXT,270,754)
        draw_text(self.screen,self.font_tiny,'Gesture: left 1/2/3 selects room, right open=ON, right fist=OFF | GUI keys: 1/2/3 O F Space L V A C H D',MUTED,64,779)

    def draw_room(self,r):
        selected=r.key==self.selected_room; rounded(self.screen,ROOM_ON if r.master else ROOM_OFF,r.rect,18)
        pygame.draw.rect(self.screen,ROOM_SELECTED if selected else WALL,r.rect,width=4 if selected else 3,border_radius=18)
        if r.master: rect_alpha(self.screen,(80,170,120),r.rect.inflate(-12,-12),28,14)
        draw_text(self.screen,self.font_room,r.label,TEXT,r.rect.x+22,r.rect.y+18)
        draw_text(self.screen,self.font_small,'MASTER ON' if r.master else 'MASTER OFF',GREEN if r.master else RED,r.rect.right-130,r.rect.y+22)
        if selected: draw_text(self.screen,self.font_tiny,'Selected by gesture / GUI / key',BLUE,r.rect.x+22,r.rect.y+50)
        for d in r.devices.values():
            if d.kind=='light': self.light(d)
            elif d.kind=='fan': self.fan(d)
            elif d.kind=='ac': self.ac(d)
            elif d.kind=='curtain': self.curtain(d)
            elif d.kind=='heater': self.heater(d)
            elif d.kind=='door': self.door(r,d)

    def light(self,d):
        x,y=d.pos; d.rect=pygame.Rect(x-48,y-56,96,112)
        if d.state: circle_alpha(self.screen,YELLOW,(x,y),58,75); circle_alpha(self.screen,YELLOW,(x,y),34,105)
        pygame.draw.circle(self.screen,YELLOW if d.state else (92,98,108),(x,y-10),24)
        pygame.draw.rect(self.screen,(245,190,60) if d.state else (68,74,84),(x-14,y+10,28,20),border_radius=5)
        pygame.draw.line(self.screen,WALL_DARK,(x-18,y+34),(x+18,y+34),3); draw_text(self.screen,self.font_small,d.label,TEXT if d.state else MUTED,x,y+48,True)
    def fan(self,d):
        x,y=d.pos; d.rect=pygame.Rect(x-58,y-58,116,116); pygame.draw.circle(self.screen,(42,50,62),(x,y),43); pygame.draw.circle(self.screen,WALL_DARK,(x,y),43,3)
        a=self.fan_angle if d.state else 0
        for i in range(3):
            th=math.radians(a+i*120); tip=(x+math.cos(th)*42,y+math.sin(th)*42); l=(x+math.cos(th+.42)*14,y+math.sin(th+.42)*14); rr=(x+math.cos(th-.42)*14,y+math.sin(th-.42)*14)
            pygame.draw.polygon(self.screen,(145,220,230) if d.state else (72,80,92),[(x,y),l,tip,rr])
        pygame.draw.circle(self.screen,CYAN if d.state else (90,100,112),(x,y),13); draw_text(self.screen,self.font_small,d.label,TEXT if d.state else MUTED,x,y+58,True)
    def ac(self,d):
        x,y=d.pos; d.rect=pygame.Rect(x-70,y-50,140,120); rounded(self.screen,(235,246,255) if d.state else (80,88,98),pygame.Rect(x-58,y-35,116,46),12); pygame.draw.rect(self.screen,BLUE if d.state else (56,62,72),(x-42,y-3,84,7),border_radius=3)
        if d.state:
            for i in range(3):
                pts=[]; yy=y+22+i*18; shift=(self.wind_offset+i*14)%28
                for j in range(20): pts.append((x-45+j*5, yy+math.sin((j+shift)*.45)*5))
                pygame.draw.lines(self.screen,BLUE,False,pts,3)
        draw_text(self.screen,self.font_small,d.label,TEXT if d.state else MUTED,x,y+64,True)
    def curtain(self,d):
        x,y=d.pos; d.rect=pygame.Rect(x-78,y-58,156,120); rounded(self.screen,(72,120,160),pygame.Rect(x-64,y-34,128,60),8); pygame.draw.line(self.screen,(180,225,255),(x,y-31),(x,y+23),2); pygame.draw.line(self.screen,(180,225,255),(x-62,y-3),(x+62,y-3),2)
        col=(190,115,225) if d.state else (120,82,150); w=int(58*(1-self.curtain_anim)+20*self.curtain_anim)
        pygame.draw.rect(self.screen,col,(x-66,y-38,w,68),border_radius=8); pygame.draw.rect(self.screen,col,(x+66-w,y-38,w,68),border_radius=8)
        draw_text(self.screen,self.font_small,'OPEN' if d.state else 'CLOSED',GREEN if d.state else MUTED,x,y+38,True); draw_text(self.screen,self.font_small,d.label,TEXT if d.state else MUTED,x,y+64,True)
    def heater(self,d):
        x,y=d.pos; d.rect=pygame.Rect(x-80,y-60,160,125); rounded(self.screen,(245,245,245) if d.state else (88,94,104),pygame.Rect(x-48,y-44,96,74),14); pygame.draw.rect(self.screen,ORANGE if d.state else WALL_DARK,(x-48,y-44,96,74),3,border_radius=14)
        pygame.draw.circle(self.screen,ORANGE if d.state else (70,76,86),(x+24,y-8),10); pygame.draw.line(self.screen,BLUE if d.state else WALL_DARK,(x,y+30),(x,y+54),5); pygame.draw.circle(self.screen,BLUE if d.state else WALL_DARK,(x,y+58),6)
        if d.state:
            for i in range(4): pygame.draw.circle(self.screen,CYAN,(int(x-35+i*22),int(y+48-((self.bubble_phase+i*11)%35))),5,2)
        draw_text(self.screen,self.font_small,d.label,TEXT if d.state else MUTED,x,y+76,True)
    def door(self,r,d):
        x,y=d.pos; d.rect=pygame.Rect(x-70,y-70,140,120); hinge=(x-10,y); angle=math.radians(-self.door_angles[r.key] if d.state else 0); end=(hinge[0]+math.cos(angle)*62,hinge[1]+math.sin(angle)*62)
        pygame.draw.line(self.screen,WALL,(hinge[0],hinge[1]-34),(hinge[0],hinge[1]+34),5); pygame.draw.arc(self.screen,WALL_DARK,pygame.Rect(hinge[0]-2,hinge[1]-66,132,132),-math.radians(70),0,2); pygame.draw.line(self.screen,GREEN if d.state else (160,112,82),hinge,end,10); pygame.draw.circle(self.screen,WALL,hinge,6)
        draw_text(self.screen,self.font_small,'OPEN' if d.state else 'CLOSED',GREEN if d.state else MUTED,x+20,y+38,True); draw_text(self.screen,self.font_small,d.label,TEXT if d.state else MUTED,x+20,y+62,True)

if __name__=='__main__': HomeVisualizerNode()
