# movies/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # WebSocket 연결을 수락합니다.
        self.room_name = "upload_progress"
        self.room_group_name = f'upload_{self.room_name}'

        # 그룹에 가입합니다.
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # 연결이 종료될 때 그룹에서 제외합니다.
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # 클라이언트로부터 받은 데이터를 처리합니다 (필요하다면).
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # 업로드 상태를 그룹에 전송합니다.
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def upload_progress(self, event):
        # 서버에서 업로드 진행 상태를 클라이언트로 보냅니다.
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
